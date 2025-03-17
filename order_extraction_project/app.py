# app.py

from flask import Flask, request, jsonify
import re
import pandas as pd
from PyPDF2 import PdfReader
import io

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Read the PDF file from the request
    pdf_path = io.BytesIO(file.read())
    reader = PdfReader(pdf_path)
    
    data = []
    for page in reader.pages:
        text = page.extract_text()
        lines = text.split('\n')

        order_id = ""
        order_date = ""
        deliver_to = ""
        phone = ""
        delivery_address = ""
        total = 0.0

        for idx, line in enumerate(lines):
            if "Order ID" in line:
                match_id = re.search(r"Order ID\s*(\d+)", line)
                if match_id:
                    order_id = match_id.group(1)
                else:
                    if idx + 1 < len(lines):
                        next_line_match = re.search(r"(\d+)", lines[idx + 1])
                        if next_line_match:
                            order_id = next_line_match.group(1)

            if "Order Date" in line:
                match_date = re.search(r"Order Date:\s*(.*)", line)
                if match_date:
                    order_date = match_date.group(1).strip()
                else:
                    if idx + 1 < len(lines):
                        order_date = lines[idx + 1].strip()

            if "Deliver To:" in line:
                dt_match = re.search(r"Deliver To:\s*(.*)", line)
                if dt_match:
                    dt_str = dt_match.group(1).strip()
                    phone_match = re.search(r"(?i)phone:\s*(\d+)", dt_str)
                    if phone_match:
                        phone = phone_match.group(1)
                        dt_str = re.sub(r"(?i)phone:\s*\d+", "", dt_str).strip()
                    deliver_to = dt_str

            if "Delivery Address:" in line:
                addr_lines = []
                da_match = re.search(r"Delivery Address:\s*(.*)", line)
                if da_match:
                    possible_addr = da_match.group(1).strip()
                    if possible_addr and not re.search(r'Bill To|Billing Address', possible_addr, re.IGNORECASE):
                        addr_lines.append(possible_addr)
                for j in range(1, 10):
                    if idx + j < len(lines):
                        next_line = lines[idx + j].strip()
                        if "Bill To" in next_line or "Billing Address" in next_line:
                            break
                        addr_lines.append(next_line)
                    else:
                        break

                delivery_address = ', '.join(addr_lines)

            if "Total:" in line:
                total_match = re.search(r'Total:\s*([\d,]+\.\d+|\d+)', line)
                if total_match:
                    total = float(total_match.group(1).replace(',', ''))

        if order_id:
            data.append({
                "Order ID": order_id,
                "Order Date": order_date,
                "Deliver To": deliver_to,
                "Phone": phone,
                "Delivery Address": delivery_address,
                "Total": total
            })

    df = pd.DataFrame(data)
    total_sum = df["Total"].sum()
    total_orders = len(df)
    summary_row = {
        "Order ID": "TOTAL SUMMARY",
        "Order Date": "",
        "Deliver To": "",
        "Phone": "",
        "Delivery Address": "",
        "Total": total_sum
    }
    df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

    # Save to Excel and return as response
    output_excel = "Extracted_Order_Details.xlsx"
    df.to_excel(output_excel, index=False)

    return jsonify({"message": "File processed successfully", "filename": output_excel})


if __name__ == '__main__':
    app.run(debug=True)
