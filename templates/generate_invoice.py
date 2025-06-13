from weasyprint import HTML
from datetime import datetime

# Sample Invoice Data
class Invoice:
    def __init__(self, id, customer_name, customer_email, date, items):
        self.id = id
        self.customer_name = customer_name
        self.customer_email = customer_email
        self.date = date
        self.items = items
        self.total_amount = sum(item['quantity'] * item['price'] for item in items)

class InvoiceItem:
    def __init__(self, product_name, quantity, price):
        self.product_name = product_name
        self.quantity = quantity
        self.price = price

# Function to generate the invoice PDF
def generate_pdf_from_template(invoice):
    # Specify the path to your HTML template
    template_path = 'D:/HareKrishna/templates/invoice_template.html'

    # Use WeasyPrint to generate PDF from HTML template
    pdf_file = f'D:/HareKrishna/invoice_{invoice.id}.pdf'  # Output PDF location
    HTML(template_path).write_pdf(pdf_file)

    print(f'Invoice PDF saved at: {pdf_file}')

# Example usage
items = [
    InvoiceItem("Product 1", 2, 100.00),
    InvoiceItem("Product 2", 1, 150.00),
    InvoiceItem("Product 3", 3, 200.00),
]

invoice = Invoice(1, "Mohammed Irfan", "if1905630109@gmail.com", datetime.now(), items)
generate_pdf_from_template(invoice)
