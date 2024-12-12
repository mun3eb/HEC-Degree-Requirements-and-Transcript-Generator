import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import seaborn as sns
import streamlit as st
from fpdf import FPDF
from io import BytesIO
import pdfkit

hec_requirements = {
    'General Education': 19,
    'University Electives': 12,
    'Mathematics & Science Foundation': 12,
    'Computing Core': 39,
    'Domain CS Core': 24,
    'Domain CS Electives': 15,
    'Domain CS Supporting': 9
}

category_mapping = {
    'General Education': [
        'English Composition & Comprehension', 'Technical & Business Writing',
        'Communication & Presentation Skills', 'Professional Practices',
        'Intro to Info. & Comm. Technologies', 'Pakistan Studies', 'Islamic Studies/ Ethics'
    ],
    'University Electives': [
        'Foreign Language', 'Social Service', 'Management Related', 'Social Science Related', 'Economy Related'
    ],
    'Mathematics & Science Foundation': [
        'Calculus & Analytical Geometry', 'Probability & Statistics', 'Linear Algebra', 'Applied Physics'
    ],
    'Computing Core': [
        'Programming Fundamentals', 'Object Oriented Programming', 'Data Structures & Algorithms', 'Discrete Structures',
        'Operating Systems', 'Database Systems', 'Software Engineering', 'Computer Networks', 'Information Security',
        'Final Year Project'
    ],
    'Domain CS Core': [
        'Compiler Construction', 'Comp. Organization & Assembly Language', 'Digital Logic Design', 'Design & Analysis of Algorithms',
        'Parallel & Distributed Computing', 'Artificial Intelligence', 'Theory of Automata'
    ],
    'Domain CS Electives': [
        'CS Elective 1', 'CS Elective 2', 'CS Elective 3', 'CS Elective 4', 'CS Elective 5'
    ],
    'Domain CS Supporting': [
        'Differential Equations', 'Multi-variate Calculus', 'Graph Theory', 'Theory of Programming Languages', 'Numerical Computing'
    ]
}

grade_mapping = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0, 'S': 0.0
}

def categorize_courses(course_name):
    for category, keywords in category_mapping.items():
        if any(keyword.lower() in course_name.lower() for keyword in keywords):
            return category
    return 'Unknown'

def filter_passed_courses(df):
    df = df[~df['grade'].isin(['S', 'F'])].copy()

    df['grade_points'] = df['grade'].map(grade_mapping)
    df = df[df['points'] >= 1.0]

    df = df.loc[df.groupby('courseName')['points'].idxmax()]

    return df

def validate_degree_requirements(df):
    df = df.copy()
    df['category'] = df['courseName'].apply(categorize_courses)

    # Handle repeated courses
    df['course_identifier'] = df['courseName'].str.replace(r'R-\d+', '', regex=True).str.strip()  # Remove R-1, R-2 etc.
    df_unique = df.groupby('course_identifier').agg({
        'creditHour': 'sum',
        'points': 'max',  # Take highest grade point
        'category': 'first'  # Keep the category
    }).reset_index()

    category_credits = df_unique.groupby('category')['creditHour'].sum()
    total_credits = df_unique['creditHour'].sum()

    compliance = {}
    for category, required_credits in hec_requirements.items():
        category_credits_sum = category_credits.get(category, 0)
        compliance[category] = {
            'credits_obtained': category_credits_sum,
            'credits_required': required_credits,
            'compliance': category_credits_sum >= required_credits
        }

    return compliance, total_credits, category_credits

def display_compliance_table(df_compliance):
    compliance_data = []
    for category, result in df_compliance.items():
        compliance_data.append({
            'Category': category,
            'Credits Obtained': result['credits_obtained'],
            'Credits Required': result['credits_required'],
            'Compliance Status': 'Met' if result['compliance'] else 'Not Met'
        })

    compliance_df = pd.DataFrame(compliance_data)
    print("\nDegree Requirements Compliance:")
    print(compliance_df)
    return compliance_df

def generate_transcript_csv(df_passed, file_name="transcript.csv"):
    df_transcript = df_passed[['courseName', 'creditHour', 'grade']]
    df_transcript.to_csv(file_name, index=False)
    print(f"\nTranscript has been saved to {file_name}")

def generate_status_text_file(df_compliance, file_name="status.txt"):
    all_met = all(result['compliance'] for result in df_compliance.values())

    status_message = "Congratulations! You have fulfilled the HEC degree requirements." if all_met else "Unfortunately, you have not fulfilled the HEC degree requirements."

    with open(file_name, 'w') as f:
        f.write(status_message + "\n\n")  # Write overall status
        f.write("Compliance Details:\n")

        for category, result in df_compliance.items():
            compliance_status = "Met" if result['compliance'] else "Not Met"
            f.write(f"{category}: {result['credits_obtained']}/{result['credits_required']} - Status: {compliance_status}\n")
    
    print(f"\nStudent status has been saved to {file_name}")


def plot_credit_distribution(df_compliance):
    categories = list(hec_requirements.keys())

    student_credits = [df_compliance.get(cat, {}).get('credits_obtained', 0) for cat in categories]
    required_credits = [hec_requirements[cat] for cat in categories]

    df_comparison = pd.DataFrame({
        'Category': categories,
        'Credits Obtained': student_credits,
        'Required Credits': required_credits
    })

    df_comparison.set_index('Category').plot(kind='bar', figsize=(12, 8))
    plt.title('Credit Distribution Comparison')
    plt.xlabel('Category')
    plt.ylabel('Credits')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

def plot_pie_chart(df_compliance):
    category_credits = [df_compliance.get(cat, {}).get('credits_obtained', 0) for cat in hec_requirements.keys()]

    plt.figure(figsize=(8, 8))
    plt.pie(category_credits, labels=hec_requirements.keys(), autopct='%1.1f%%', startangle=90)
    plt.title('Proportion of Credits Obtained by Category')
    plt.axis('equal')
    plt.show()

def calculate_overall_gpa(df):
    df_passed = filter_passed_courses(df)

    total_points = (df_passed['grade_points'] * df_passed['creditHour']).sum()
    total_credits = df_passed['creditHour'].sum()

    if total_credits > 0:
        overall_gpa = total_points / total_credits
    else:
        overall_gpa = 0.0

    return overall_gpa

def plot_gpa_distribution(df):
    df_passed = filter_passed_courses(df)

    df_passed['grade_points'] = df_passed['grade'].map(grade_mapping)

    plt.figure(figsize=(10, 6))
    sns.histplot(df_passed['grade_points'], bins=10, kde=True, color='skyblue', edgecolor='black')
    plt.title('Overall GPA Distribution')
    plt.xlabel('GPA')
    plt.ylabel('Number of Courses')
    plt.tight_layout()
    plt.show()
    

import os
from fpdf import FPDF
import tempfile

def transcript_pdf(df, overall_gpa, compliance, total_credits):
    # Create a PDF instance using FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'National University of Computer and Emerging Sciences', ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Transcript', ln=True, align="C")
    pdf.ln(10)

    # Overall GPA
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Your Overall GPA is: {overall_gpa:.2f}", ln=True)
    pdf.ln(10)

    # Compliance Summary
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Compliance Summary", ln=True)
    pdf.set_font("Arial", '', 12)
    for category, result in compliance.items():
        status = 'Met' if result['compliance'] else 'Not Met'
        pdf.cell(0, 10, f"{category}: Obtained {result['credits_obtained']}/{result['credits_required']} - Status: {status}", ln=True)
    pdf.ln(10)

    # Total Credits
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Total Credits Obtained: {total_credits}", ln=True)
    pdf.ln(10)

    # Transcript Table
    pdf.set_font("Arial", 'B', 12)
    # Add table headers
    headers = df.columns.tolist()
    for header in headers:
        pdf.cell(40, 10, header, border=1, align='C')
    pdf.ln()

    # Add table rows
    pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        for col in headers:
            pdf.cell(40, 10, str(row[col]), border=1, align='C')
        pdf.ln()

    # Save PDF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf.output(tmpfile.name)
        tmpfile_path = tmpfile.name  # Save the file path for later use

    return tmpfile_path


def main():
    st.title('Degree Requirements and Transcript Generator')

    st.sidebar.header("Upload your CSV file")
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            # Read the file into a pandas dataframe
            df = pd.read_csv(uploaded_file)

            st.subheader("Student Data Preview")
            st.write(df.head())

            overall_gpa = calculate_overall_gpa(df)
            st.subheader(f"Overall GPA: {overall_gpa:.2f}")

            df_passed = filter_passed_courses(df)


            st.subheader("Degree Requirements Compliance")
            compliance, total_credits, category_credits = validate_degree_requirements(df_passed)
            df_compliance = display_compliance_table(compliance)
            st.table(df_compliance)

            st.subheader("Credit Distribution Comparison")
            plot_credit_distribution(compliance)
            st.pyplot()

            # Plot Pie Chart for Credit Proportion
            st.subheader("Proportion of Credits Obtained by Category")
            plot_pie_chart(compliance)
            st.pyplot()

            st.subheader("Generate Transcript CSV")
            if st.button('Generate Transcript CSV'):
                generate_transcript_csv(df, file_name="transcript.csv")
                st.success("Transcript CSV has been saved!")

            st.subheader("Generate Status File")
            if st.button('Generate Status Text File'):
                generate_status_text_file(compliance, file_name="status.txt")
                with open("status.txt", "r") as file:
                    status_content = file.read()
                st.text(status_content)
                st.success("Status file has been saved!")
        
            # Determine if the user has fulfilled the degree requirements
            all_met = all(result['compliance'] for result in compliance.values())

            if all_met:
                if st.button("Generate Transcript PDF"):
                    pdf_file_path = transcript_pdf(df, overall_gpa, compliance, total_credits)
                
                if pdf_file_path:
                    with open(pdf_file_path, "rb") as f:
                        pdf_data = f.read()
                st.download_button(
            label="Download Transcript PDF",
            data=pdf_data,
            file_name="transcript.pdf",
            mime="application/pdf"
        )

        except Exception as e:
            st.error(f"Error reading the file: {e}")

if __name__ == "__main__":
    main()

