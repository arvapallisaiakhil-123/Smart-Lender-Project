from flask import Flask, render_template, request, redirect, url_for, session
from database import *
from datetime import datetime
import pickle
import numpy as np
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
import os
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
app = Flask(__name__)
app.secret_key = "smart_lender_secret_key"

# Load model and scaler
model = pickle.load(open("models/rdf.pkl", "rb"))
scaler = pickle.load(open("models/scale1.pkl", "rb"))

create_database()
create_users_table()

@app.route("/register")
def register():

    return render_template("register.html")

@app.route("/login")
def login():

    return render_template("login.html")

@app.route("/logout")

def logout():

    session.clear()

    return redirect("/")

@app.route("/")
def home():
    return render_template("home.html")
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
       return redirect("/login")

    total = get_total_predictions()

    approved = get_total_approved()

    rejected = get_total_rejected()

    accuracy = 0

    if total > 0:
        accuracy = round((approved / total) * 100, 2)

    recent = get_all_predictions()[:5]

    return render_template(
        "dashboard.html",
        total=total,
        approved=approved,
        rejected=rejected,
        accuracy=accuracy,
        recent=recent
    )
@app.route("/loginUser", methods=["POST"])
def loginUser():

    email = request.form["email"]
    password = request.form["password"]

    user = login_user(email, password)

    if user:

        session["user"] = user[1]
        session["user_id"] = user[0]
        session["email"] = user[2]

        return redirect("/dashboard")

    return render_template(
        "login.html",
        error="Invalid Email or Password"
    )
@app.route("/registerUser", methods=["POST"])
def registerUser():

    fullname = request.form["fullname"]
    email = request.form["email"]
    password = request.form["password"]

    if email_exists(email):

        return render_template(
            "register.html",
            error="Email already exists!"
        )

    success = register_user(fullname, email, password)

    if success:

        return redirect("/login")

    return render_template(
        "register.html",
        error="Registration failed!"
    )

@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    data = get_all_predictions()

    return render_template(
        "history.html",
        data=data
    )
@app.route("/predict")
def predict():

    if "user" not in session:
        return redirect("/login")

    return render_template("predict.html")

@app.route("/submit", methods=["POST"])
def submit():

    if "user" not in session:
        return redirect("/login")

    # -------------------------
    # Get Form Data
    # -------------------------

    applicant_name = request.form["applicant_name"]

    gender = float(request.form["gender"])
    married = float(request.form["married"])
    dependents = float(request.form["dependents"])
    education = float(request.form["education"])
    self_employed = float(request.form["self_employed"])

    applicant_income = float(request.form["applicant_income"])
    coapplicant_income = float(request.form["coapplicant_income"])

    loan_amount = float(request.form["loan_amount"])
    loan_term = float(request.form["loan_term"])

    credit_history = float(request.form["credit_history"])
    property_area = float(request.form["property_area"])

    # -------------------------
    # Prepare Features
    # -------------------------

    features = np.array([[
        gender,
        married,
        dependents,
        education,
        self_employed,
        applicant_income,
        coapplicant_income,
        loan_amount,
        loan_term,
        credit_history,
        property_area
    ]])

    

    # -------------------------
    # Scale Features
    # -------------------------

    features = scaler.transform(features)

    # -------------------------
    # Predict
    # -------------------------

    prediction = model.predict(features)

    probability = model.predict_proba(features)

    confidence = round(float(max(probability[0])) * 100, 2)

    # -------------------------
    # Risk Level
    # -------------------------

    if confidence >= 90:
        risk = "Low"

    elif confidence >= 75:
        risk = "Medium"

    else:
        risk = "High"

    # -------------------------
    # Final Result
    # -------------------------

    if prediction[0] == 1:
        result = "Loan Approved ✅"

    else:
        result = "Loan Rejected ❌"

    # -------------------------
    # Save Prediction
    # -------------------------

    save_prediction((

        applicant_name,

        str(gender),

        str(married),

        str(dependents),

        str(education),

        str(self_employed),

        applicant_income,

        coapplicant_income,

        loan_amount,

        loan_term,

        str(credit_history),

        str(property_area),

        result

    ))

    # -------------------------
    # Date & Time
    # -------------------------

    current_date = datetime.now().strftime("%d %B %Y")

    current_time = datetime.now().strftime("%I:%M %p")

    if credit_history == 1:
     credit_text = "Good"
    else:
     credit_text = "Poor"

    if property_area == 0:
     area_text = "Rural"
    elif property_area == 1:
     area_text = "Semi Urban"
    else:
     area_text = "Urban"

    session["report"] = {

    "applicant": str(applicant_name),

    "prediction": str(result),

    "confidence": float(confidence),

    "risk": str(risk),

    "income": float(applicant_income),

    "loan": float(loan_amount),

    "credit": str(credit_text),

    "area": str(area_text),

    "date": str(current_date),

    "time": str(current_time)

}

    # -------------------------
    # Return Result
    # -------------------------

    return render_template(

        "result.html",

        prediction=result,

        confidence=confidence,

        applicant=applicant_name,

        income=applicant_income,

        loan=loan_amount,

        credit=credit_text,
area=area_text,

        risk=risk,

        current_date=current_date,

        current_time=current_time

    )

@app.route("/download_pdf")
def download_pdf():

    if "report" not in session:
        return redirect("/dashboard")

    report = session["report"]

    filename = os.path.join(os.getcwd(), "Loan_Report.pdf")

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    elements = []

    report_id = "SL-" + datetime.now().strftime("%Y%m%d%H%M%S")

    elements.append(
    Paragraph(
        "<font size='24' color='blue'><b>SMART LENDER</b></font>",
        styles["Title"]
    )
)

    elements.append(
    Paragraph(
        "<b>AI Powered Loan Eligibility Prediction Report</b>",
        styles["Heading2"]
    )
)

    elements.append(
    Paragraph("<br/>", styles["Normal"])
)    
    status_style = ParagraphStyle(
    'Status',
    parent=styles['Heading1'],
    alignment=TA_CENTER,
    textColor=colors.white,
    backColor=colors.green if status == "APPROVED" else colors.red,
    spaceAfter=20,
    spaceBefore=10
)

    elements.append(
    Paragraph(status, status_style)
)
   

    elements.append(
        Paragraph("Loan Eligibility Report", styles["Heading2"])
    )

    elements.append(
        Paragraph("<br/>", styles["Normal"])
    )
    report_id = "SL-" + datetime.now().strftime("%Y%m%d%H%M%S")

    status = "APPROVED" if "Approved" in report["prediction"] else "REJECTED"

    data = [

    ["Report ID", report_id],

    ["Applicant", report["applicant"]],

    ["Prediction Status", status],

    ["Confidence", f"{report['confidence']}%"],

    ["Risk", report["risk"]],

    ["Income", f"Rs. {report['income']:,.0f}"],

    ["Loan Amount", f"Rs. {report['loan']:,.0f}"],

    ["Credit History", report["credit"]],

    ["Property Area", report["area"]],

    ["Date", report["date"]],

    ["Time", report["time"]]

]

    table = Table(data, colWidths=[170, 250])

    table.setStyle(TableStyle([

    ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0F62FE")),

    ('TEXTCOLOR',(0,0),(-1,0),colors.white),

    ('BACKGROUND',(0,1),(0,-1),colors.HexColor("#F3F6FA")),

    ('GRID',(0,0),(-1,-1),0.5,colors.grey),

    ('FONTNAME',(0,0),(-1,-1),'Helvetica'),

    ('BOTTOMPADDING',(0,0),(-1,-1),10),

    ('TOPPADDING',(0,0),(-1,-1),10),

    ('VALIGN',(0,0),(-1,-1),'MIDDLE')

]))

    elements.append(table)

    elements.append(
    Paragraph("<br/><b>Disclaimer</b>", styles["Heading2"])
)

    elements.append(
    Paragraph(
        "This report is generated using the Smart Lender Artificial Intelligence Prediction System. "
        "The prediction is intended to assist decision-making and should not be considered the sole basis for loan approval.",
        styles["Normal"]
    )
)
    elements.append(
    Paragraph("<br/><br/>", styles["Normal"])
)

    elements.append(
    Paragraph("______________________________", styles["Normal"])
)

    elements.append(
    Paragraph("<b>Authorized Officer</b>", styles["Normal"])
)

    elements.append(
    Paragraph("Smart Lender AI System", styles["Normal"])
)

    elements.append(
    Paragraph("✔ Applicant information verified.", styles["Normal"])
)

    elements.append(
    Paragraph("✔ Credit history evaluated successfully.", styles["Normal"])
)

    elements.append(
    Paragraph("✔ AI risk assessment completed.", styles["Normal"])
)

    elements.append(
    Paragraph("✔ Loan eligibility prediction generated.", styles["Normal"])
)
    elements.append(
    Paragraph("<br/><br/>", styles["Normal"])
)

    elements.append(
    Paragraph(
        "<b>Generated by Smart Lender AI</b>",
        styles["Normal"]
    )
)

    elements.append(
    Paragraph(
        "Random Forest Classifier | Flask | MongoDB Atlas",
        styles["Normal"]
    )
)

    elements.append(
    Paragraph(
        "This report is generated automatically using Artificial Intelligence.",
        styles["Normal"]
    )
)

    doc.build(elements)
    

    return send_file(filename, as_attachment=True)
   


if __name__ == "__main__":
    app.run(debug=True)