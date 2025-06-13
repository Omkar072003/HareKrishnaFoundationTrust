from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'b722e52cf579d29b7db91f8c3c674375'
DB_PATH = "billing.db"
FONT_PATH = "static/fonts/DejaVuSans.ttf"

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "xavioussparda@gmail.com"  # Replace with your email
SMTP_PASSWORD = "hbswseehskerrcpd"  # Replace with your app password

# Register font for ₹ symbol support globally
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))
else:
    print("⚠ Warning: DejaVuSans font not found! Using default fonts (₹ may not display correctly).")

def init_db():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Drop existing tables first to ensure clean schema
    c.execute("DROP TABLE IF EXISTS messages")
    c.execute("DROP TABLE IF EXISTS invoices")
    c.execute("DROP TABLE IF EXISTS imaging_centers")
    
    # Invoices table with time_slot
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time_slot TEXT NOT NULL,
                    product TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL
                )''')
    
    # Imaging centers table
    c.execute('''CREATE TABLE IF NOT EXISTS imaging_centers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    address TEXT NOT NULL,
                    phone TEXT
                )''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    imaging_center_id INTEGER NOT NULL,
                    customer_message TEXT NOT NULL,
                    center_message TEXT NOT NULL,
                    sent_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id),
                    FOREIGN KEY (imaging_center_id) REFERENCES imaging_centers (id)
                )''')
    
    conn.commit()
    conn.close()

def migrate_existing_data():
    """Migrate existing data to new schema if needed"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if time_slot column exists
        c.execute("PRAGMA table_info(invoices)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'time_slot' not in columns:
            # Add time_slot column with a default value
            c.execute("ALTER TABLE invoices ADD COLUMN time_slot TEXT DEFAULT '09:00 AM' NOT NULL")
            conn.commit()
            print("Successfully added time_slot column")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")

# Initialize or migrate database
if os.path.exists(DB_PATH):
    migrate_existing_data()
else:
    init_db()

# Custom Jinja2 filter for datetime formatting
def datetimeformat(value, format='%Y'):
    """Custom filter to format datetime objects or 'now'."""
    if value == 'now':
        return datetime.now().strftime(format)
    return value.strftime(format) if hasattr(value, 'strftime') else value

# Register the custom filter with Jinja2
app.jinja_env.filters['datetimeformat'] = datetimeformat

def generate_customer_appointment_pdf(invoice_id, imaging_center_name):
    """Generate appointment PDF for customer"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    invoice = c.fetchone()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )

    story.append(Paragraph("Medical Appointment Confirmation", title_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(f"Dear {invoice[1]},", styles['Heading2']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Your medical imaging appointment has been scheduled.", styles['Normal']))
    story.append(Spacer(1, 12))
    
    details = [
        ["Procedure:", invoice[5]],
        ["Imaging Center:", imaging_center_name],
        ["Date:", invoice[3]],
        ["Time:", invoice[4]],
    ]
    
    font_name = "DejaVuSans" if os.path.exists(FONT_PATH) else "Helvetica"
    table = Table(details, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Important Notes:", styles['Heading3']))
    story.append(Paragraph("• Please arrive 15 minutes before your appointment", styles['Normal']))
    story.append(Paragraph("• Bring valid photo identification", styles['Normal']))
    story.append(Paragraph("• Bring your insurance card if applicable", styles['Normal']))
    story.append(Paragraph("• Wear comfortable clothing", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_center_appointment_pdf(invoice_id):
    """Generate appointment PDF for imaging center"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    invoice = c.fetchone()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )

    story.append(Paragraph("New Patient Referral", title_style))
    story.append(Spacer(1, 20))
    
    details = [
        ["Patient Name:", invoice[1]],
        ["Patient Email:", invoice[2]],
        ["Appointment Date:", invoice[3]],
        ["Appointment Time:", invoice[4]],
        ["Procedure:", invoice[5]],
        ["Quantity:", str(invoice[6])],
        ["Price:", f"₹{invoice[7]:.2f}"],
    ]
    
    font_name = "DejaVuSans" if os.path.exists(FONT_PATH) else "Helvetica"
    table = Table(details, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_invoice_pdf(invoice_id):
    """Generate PDF invoice"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    invoice = c.fetchone()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    if os.path.exists(FONT_PATH):
        pdf.setFont("DejaVuSans", 14)
    else:
        pdf.setFont("Times-Roman", 14)

    # Header
    pdf.drawString(50, 800, "MEDICAL BILLING INVOICE")
    pdf.drawString(50, 780, f"Invoice ID: {invoice[0]}")
    pdf.drawString(50, 760, f"Date: {invoice[3]}")
    pdf.drawString(50, 740, f"Time: {invoice[4]}")

    # Customer Details
    pdf.drawString(50, 720, "Bill To:")
    pdf.drawString(70, 700, f"Name: {invoice[1]}")
    pdf.drawString(70, 680, f"Email: {invoice[2]}")

    # Invoice Items
    pdf.drawString(50, 640, "INVOICE DETAILS")
    pdf.drawString(50, 620, "-" * 100)
    pdf.drawString(50, 600, "Description")
    pdf.drawString(250, 600, "Quantity")
    pdf.drawString(350, 600, "Price")
    pdf.drawString(450, 600, "Total")
    pdf.drawString(50, 580, "-" * 100)

    # Item details
    pdf.drawString(50, 560, invoice[5])  # Product
    pdf.drawString(250, 560, str(invoice[6]))  # Quantity
    pdf.drawString(350, 560, f"₹{invoice[7]:.2f}")  # Price
    total = invoice[6] * invoice[7]
    pdf.drawString(450, 560, f"₹{total:.2f}")  # Total

    # Footer
    pdf.drawString(50, 500, "-" * 100)
    pdf.drawString(350, 480, f"Total Amount: ₹{total:.2f}")
    
    pdf.drawString(50, 440, "Payment Terms:")
    pdf.drawString(70, 420, "Please make payment within 30 days")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    """Home page - display list of invoices"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT i.*, m.sent_date 
        FROM invoices i 
        LEFT JOIN messages m ON i.id = m.invoice_id 
        ORDER BY i.date DESC, i.time_slot ASC
    """)
    invoices = c.fetchall()
    conn.close()
    return render_template("index.html", invoices=invoices)

@app.route('/create', methods=["GET", "POST"])
def create_invoice():
    """Create new invoice"""
    if request.method == "POST":
        try:
            customer_name = request.form['customer_name']
            email = request.form['email']
            date = request.form['date']
            time_slot = request.form['time_slot']
            product = request.form['product']
            quantity = int(request.form['quantity'])
            price = float(request.form['price'])

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO invoices 
                (customer_name, email, date, time_slot, product, quantity, price) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_name, email, date, time_slot, product, quantity, price))
            conn.commit()
            conn.close()
            
            flash('Invoice created successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error creating invoice: {str(e)}', 'error')
            return redirect(url_for('create_invoice'))
    
    time_slots = [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
        "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
        "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
        "04:00 PM", "04:30 PM", "05:00 PM"
    ]
    
    return render_template("create_invoice.html", time_slots=time_slots)

@app.route('/manage_centers', methods=['GET', 'POST'])
def manage_centers():
    """Manage imaging centers"""
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            address = request.form['address']
            phone = request.form['phone']
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO imaging_centers 
                (name, email, address, phone) 
                VALUES (?, ?, ?, ?)
            """, (name, email, address, phone))
            conn.commit()
            conn.close()
            
            flash('Imaging center added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding imaging center: {str(e)}', 'error')
        
        return redirect(url_for('manage_centers'))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM imaging_centers ORDER BY name")
    centers = c.fetchall()
    conn.close()
    
    return render_template('manage_centers.html', centers=centers)

@app.route('/send_messages/<int:invoice_id>', methods=['GET', 'POST'])
def send_messages(invoice_id):
    """Send messages and PDFs to customer and imaging center"""
    if request.method == 'POST':
        try:
            imaging_center_id = request.form['imaging_center']
            customer_message = request.form['customer_message']
            center_message = request.form['center_message']
            
            # Get email preferences
            send_invoice = 'send_invoice' in request.form
            send_appointment = 'send_appointment' in request.form
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Get invoice details
            c.execute("SELECT customer_name, email FROM invoices WHERE id=?", (invoice_id,))
            invoice = c.fetchone()
            if invoice is None:
                raise ValueError("Invoice not found")
            
            # Get imaging center details
            c.execute("SELECT name, email FROM imaging_centers WHERE id=?", (imaging_center_id,))
            center = c.fetchone()
            if center is None:
                raise ValueError("Selected imaging center not found")
            
            # Create customer email
            customer_msg = MIMEMultipart()
            customer_msg['Subject'] = "Your Medical Imaging Appointment"
            customer_msg['From'] = SMTP_USERNAME
            customer_msg['To'] = invoice[1]
            customer_msg.attach(MIMEText(customer_message, 'plain'))
            
            # Attach PDFs based on preferences
            if send_appointment:
                customer_pdf = generate_customer_appointment_pdf(invoice_id, center[0])
                customer_pdf_part = MIMEApplication(customer_pdf.getvalue(), _subtype="pdf")
                customer_pdf_part.add_header('Content-Disposition', 'attachment', 
                                          filename=f'appointment_{invoice_id}.pdf')
                customer_msg.attach(customer_pdf_part)
            
            if send_invoice:
                invoice_pdf = generate_invoice_pdf(invoice_id)
                invoice_pdf_part = MIMEApplication(invoice_pdf.getvalue(), _subtype="pdf")
                invoice_pdf_part.add_header('Content-Disposition', 'attachment', 
                                         filename=f'invoice_{invoice_id}.pdf')
                customer_msg.attach(invoice_pdf_part)
            
            # Create center email
            center_msg = MIMEMultipart()
            center_msg['Subject'] = f"New Patient Referral - {invoice[0]}"
            center_msg['From'] = SMTP_USERNAME
            center_msg['To'] = center[1]
            center_msg.attach(MIMEText(center_message, 'plain'))
            
            center_pdf = generate_center_appointment_pdf(invoice_id)
            center_pdf_part = MIMEApplication(center_pdf.getvalue(), _subtype="pdf")
            center_pdf_part.add_header('Content-Disposition', 'attachment', 
                                     filename=f'patient_referral_{invoice_id}.pdf')
            center_msg.attach(center_pdf_part)
            
            # Send emails
            try:
                server = smtplib.SMTP(SMPTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                
                server.send_message(customer_msg)
                server.send_message(center_msg)
                server.quit()
                
                # Record messages in database
                c.execute("""
                    INSERT INTO messages 
                    (invoice_id, imaging_center_id, customer_message, center_message, sent_date, status) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id, 
                    imaging_center_id, 
                    customer_message, 
                    center_message, 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'SENT'
                ))
                conn.commit()
                flash('Messages and PDFs sent successfully!', 'success')
                
            except Exception as e:
                flash(f'Error sending emails: {str(e)}', 'error')
            
        except Exception as e:
            flash(f'Error processing request: {str(e)}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('index'))
    
    # Get invoice and centers for the form
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    invoice = c.fetchone()
    
    c.execute("SELECT * FROM imaging_centers ORDER BY name")
    centers = c.fetchall()
    
    conn.close()
    return render_template('send_messages.html', invoice=invoice, centers=centers)

@app.route('/download_customer_pdf/<int:invoice_id>/<int:center_id>')
def download_customer_pdf(invoice_id, center_id):
    """Download customer appointment PDF"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM imaging_centers WHERE id=?", (center_id,))
    center = c.fetchone()
    conn.close()
    
    if center is None:
        flash('Imaging center not found!', 'error')
        return redirect(url_for('index'))
    
    pdf_buffer = generate_customer_appointment_pdf(invoice_id, center[0])
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'appointment_{invoice_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/download_center_pdf/<int:invoice_id>')
def download_center_pdf(invoice_id):
    """Download imaging center referral PDF"""
    pdf_buffer = generate_center_appointment_pdf(invoice_id)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'patient_referral_{invoice_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/invoice/<int:invoice_id>/pdf')
def download_invoice_pdf(invoice_id):
    """Download invoice PDF"""
    pdf_buffer = generate_invoice_pdf(invoice_id)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'invoice_{invoice_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    """Delete an invoice"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Delete related messages first (due to foreign key constraint)
        c.execute("DELETE FROM messages WHERE invoice_id = ?", (invoice_id,))
        c.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        
        conn.commit()
        conn.close()
        
        flash('Invoice deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting invoice: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/view_messages/<int:invoice_id>')
def view_messages(invoice_id):
    """View message history for an invoice"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT m.*, ic.name as center_name 
        FROM messages m 
        JOIN imaging_centers ic ON m.imaging_center_id = ic.id 
        WHERE m.invoice_id = ? 
        ORDER BY m.sent_date DESC
    """, (invoice_id,))
    messages = c.fetchall()
    
    c.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice = c.fetchone()
    
    conn.close()
    
    return render_template('view_messages.html', messages=messages, invoice=invoice)

if __name__ == '__main__':
    app.jinja_env.auto_reload = True  # Added to ensure template changes are picked up
    app.run(debug=True)