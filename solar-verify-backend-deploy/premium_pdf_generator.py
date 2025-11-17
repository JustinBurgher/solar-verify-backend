"""
Premium PDF Report Generator for SolarVerify
Generates comprehensive solar quote analysis reports
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import io
import base64


def generate_premium_pdf_report(analysis_data):
    """
    Generate a comprehensive PDF report from premium analysis data
    
    Args:
        analysis_data: Dictionary containing all analysis results
        
    Returns:
        BytesIO object containing the PDF
    """
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#0f766e'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        spaceAfter=10,
        alignment=TA_JUSTIFY
    )
    
    # Extract data
    grade = analysis_data.get('grade', 'N/A')
    verdict = analysis_data.get('verdict', '')
    basic = analysis_data.get('basic_analysis', {})
    components = analysis_data.get('component_analysis', {})
    installation = analysis_data.get('installation_analysis', {})
    installer = analysis_data.get('installer_analysis', {})
    red_flags = analysis_data.get('red_flags', [])
    considerations = analysis_data.get('things_to_consider', [])
    questions = analysis_data.get('questions_to_ask', [])
    
    # ===== COVER PAGE =====
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("SolarVerify", title_style))
    elements.append(Paragraph("Premium Solar Quote Analysis Report", heading_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Grade display
    grade_color = {
        'A': colors.HexColor('#10b981'),
        'B': colors.HexColor('#3b82f6'),
        'C': colors.HexColor('#f59e0b'),
        'D': colors.HexColor('#ef4444'),
        'F': colors.HexColor('#dc2626')
    }.get(grade, colors.grey)
    
    grade_table_data = [[Paragraph(f"<font size=48 color='white'><b>{grade}</b></font>", body_style)]]
    grade_table = Table(grade_table_data, colWidths=[2*inch])
    grade_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), grade_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 30),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
    ]))
    
    elements.append(grade_table)
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"<b>{verdict}</b>", body_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Report metadata
    report_date = datetime.now().strftime("%d %B %Y")
    elements.append(Paragraph(f"<i>Report Generated: {report_date}</i>", body_style))
    elements.append(Paragraph(f"<i>Location: {basic.get('location', 'Not specified')}</i>", body_style))
    
    elements.append(PageBreak())
    
    # ===== EXECUTIVE SUMMARY =====
    elements.append(Paragraph("Executive Summary", heading_style))
    
    summary_data = [
        ['System Size', f"{basic.get('system_size', 0)} kW"],
        ['Total Cost', f"£{basic.get('total_price', 0):,.2f}"],
        ['Price per kW', f"£{basic.get('price_per_kw', 0):,.2f}"],
        ['Market Average', f"£{basic.get('market_average', 0):,.2f}/kW"],
        ['Grade', grade],
    ]
    
    if basic.get('potential_savings', 0) > 0:
        summary_data.append(['Potential Savings', f"£{basic.get('potential_savings', 0):,.2f}"])
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0f2f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== RED FLAGS =====
    if red_flags:
        elements.append(Paragraph("⚠️ Critical Issues Identified", heading_style))
        elements.append(Paragraph(
            "The following critical issues require immediate attention before proceeding with this installation:",
            body_style
        ))
        elements.append(Spacer(1, 0.1*inch))
        
        for flag in red_flags:
            elements.append(Paragraph(f"• {flag}", body_style))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # ===== COMPONENT ANALYSIS =====
    elements.append(Paragraph("Component Analysis", heading_style))
    
    # Solar Panels
    if 'panels' in components:
        panels = components['panels']
        elements.append(Paragraph("Solar Panels", subheading_style))
        
        panel_data = [
            ['Brand', panels.get('brand', 'N/A')],
            ['Model', panels.get('model', 'N/A')],
            ['Wattage per Panel', f"{panels.get('wattage', 0)} W"],
            ['Number of Panels', str(panels.get('quantity', 0))],
            ['Calculated System Size', f"{panels.get('calculated_system_size', 0)} kW"],
            ['Size Verification', '✓ Matches' if panels.get('matches_quoted_size') else '✗ Mismatch'],
        ]
        
        panel_table = Table(panel_data, colWidths=[2.5*inch, 3*inch])
        panel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0fdfa')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(panel_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Inverter
    if 'inverter' in components:
        inverter = components['inverter']
        elements.append(Paragraph("Inverter", subheading_style))
        
        inverter_data = [
            ['Brand', inverter.get('brand', 'N/A')],
            ['Model', inverter.get('model', 'N/A')],
            ['Type', inverter.get('type', 'N/A').replace('_', ' ').title()],
            ['Capacity', f"{inverter.get('capacity', 0)} kW"],
            ['Sizing Ratio', f"{inverter.get('sizing_ratio', 0)}%"],
            ['Sizing Assessment', '✓ Optimal' if inverter.get('properly_sized') else '⚠ Review Needed'],
        ]
        
        inverter_table = Table(inverter_data, colWidths=[2.5*inch, 3*inch])
        inverter_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0fdfa')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(inverter_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Battery
    if 'battery' in components:
        battery = components['battery']
        elements.append(Paragraph("Battery Storage", subheading_style))
        
        battery_data = [
            ['Brand', battery.get('brand', 'N/A')],
            ['Model', battery.get('model', 'N/A')],
            ['Capacity per Unit', f"{battery.get('capacity_per_unit', 0)} kWh"],
            ['Number of Units', str(battery.get('quantity', 0))],
            ['Total Capacity', f"{battery.get('total_capacity', 0)} kWh"],
            ['Warranty', f"{battery.get('warranty_years', 0)} years"],
            ['Sizing Assessment', '✓ Appropriate' if battery.get('sizing_appropriate') else '⚠ Review Needed'],
        ]
        
        battery_table = Table(battery_data, colWidths=[2.5*inch, 3*inch])
        battery_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0fdfa')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(battery_table)
        elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== INSTALLATION DETAILS =====
    if installation:
        elements.append(Paragraph("Installation Details", heading_style))
        
        if 'scaffolding' in installation:
            scaff = installation['scaffolding']
            elements.append(Paragraph(f"<b>Scaffolding:</b> Included (£{scaff.get('cost', 0):,.2f})", body_style))
        
        if 'bird_protection' in installation:
            bird = installation['bird_protection']
            elements.append(Paragraph(f"<b>Bird Protection:</b> Included (£{bird.get('cost', 0):,.2f})", body_style))
        
        if 'roof' in installation:
            roof = installation['roof']
            elements.append(Paragraph(
                f"<b>Roof Type:</b> {roof.get('type', 'N/A').title()} | "
                f"<b>Material:</b> {roof.get('material', 'N/A').title()}",
                body_style
            ))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # ===== INSTALLER INFORMATION =====
    elements.append(Paragraph("Installer Information", heading_style))
    
    installer_data = [
        ['Company Name', installer.get('company', 'N/A')],
        ['Location', installer.get('location', 'N/A')],
        ['MCS Certified', '✓ Yes' if installer.get('mcs_registered') else '✗ No'],
    ]
    
    if installer.get('mcs_number'):
        installer_data.append(['MCS Number', installer.get('mcs_number')])
    
    if installer.get('years_in_business'):
        installer_data.append(['Years in Business', str(installer.get('years_in_business'))])
    
    if installer.get('warranty_years'):
        installer_data.append(['Installation Warranty', f"{installer.get('warranty_years')} years"])
    
    if installer.get('installation_timeline'):
        installer_data.append(['Timeline', installer.get('installation_timeline')])
    
    installer_table = Table(installer_data, colWidths=[2.5*inch, 3*inch])
    installer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0fdfa')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(installer_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== THINGS TO CONSIDER =====
    if considerations:
        elements.append(Paragraph("Things to Consider", heading_style))
        elements.append(Paragraph(
            "The following points warrant further consideration when evaluating this quote:",
            body_style
        ))
        elements.append(Spacer(1, 0.1*inch))
        
        for consideration in considerations:
            elements.append(Paragraph(f"• {consideration}", body_style))
        
        elements.append(Spacer(1, 0.3*inch))
    
    # ===== QUESTIONS TO ASK =====
    if questions:
        elements.append(Paragraph("Questions to Ask Your Installer", heading_style))
        elements.append(Paragraph(
            "We recommend asking your installer the following questions to clarify important details:",
            body_style
        ))
        elements.append(Spacer(1, 0.1*inch))
        
        for i, question in enumerate(questions, 1):
            elements.append(Paragraph(f"{i}. {question}", body_style))
        
        elements.append(Spacer(1, 0.3*inch))
    
    elements.append(PageBreak())
    
    # ===== DISCLAIMER =====
    elements.append(Paragraph("Important Disclaimer", heading_style))
    elements.append(Paragraph(
        "This report provides an independent analysis of your solar quote based on the information provided. "
        "It is intended for informational purposes only and should not be considered as professional advice. "
        "SolarVerify is not responsible for any decisions made based on this report.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(
        "We strongly recommend conducting your own due diligence, obtaining multiple quotes, and consulting "
        "with qualified professionals before making any installation decisions. Always verify installer credentials, "
        "check references, and ensure all agreements are documented in writing.",
        body_style
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Paragraph(
        "<i>Report generated by SolarVerify Premium Analysis Service</i><br/>"
        "<i>For support, contact: justinburgher@solarverify.co.uk</i><br/>"
        f"<i>© {datetime.now().year} SolarVerify. All rights reserved.</i>",
        body_style
    ))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    buffer.seek(0)
    return buffer


def send_premium_report_email(user_email, analysis_data, sendgrid_client):
    """
    Send premium analysis report via email with PDF attachment
    
    Args:
        user_email: Recipient email address
        analysis_data: Analysis results dictionary
        sendgrid_client: SendGrid API client instance
        
    Returns:
        Boolean indicating success
    """
    try:
        # Generate PDF
        pdf_buffer = generate_premium_pdf_report(analysis_data)
        pdf_data = pdf_buffer.read()
        
        # Encode PDF for email attachment
        encoded_pdf = base64.b64encode(pdf_data).decode()
        
        # Create email
        grade = analysis_data.get('grade', 'N/A')
        system_size = analysis_data.get('basic_analysis', {}).get('system_size', 0)
        
        message = Mail(
            from_email='justinburgher@solarverify.co.uk',
            to_emails=user_email,
            subject=f'Your SolarVerify Premium Analysis Report (Grade: {grade})',
            html_content=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #0d9488 0%, #2563eb 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0;">SolarVerify Premium</h1>
                        <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Your Comprehensive Solar Quote Analysis</p>
                    </div>
                    
                    <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
                        <h2 style="color: #0d9488; margin-top: 0;">Analysis Complete!</h2>
                        
                        <p>Thank you for using SolarVerify Premium. Your comprehensive solar quote analysis is ready.</p>
                        
                        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0d9488;">
                            <h3 style="margin-top: 0; color: #0d9488;">Your Quote Summary</h3>
                            <p style="margin: 5px 0;"><strong>System Size:</strong> {system_size} kW</p>
                            <p style="margin: 5px 0;"><strong>Overall Grade:</strong> <span style="font-size: 24px; font-weight: bold; color: #0d9488;">{grade}</span></p>
                        </div>
                        
                        <p><strong>Your detailed PDF report is attached to this email.</strong> It includes:</p>
                        <ul style="padding-left: 20px;">
                            <li>Detailed component analysis (panels, inverter, battery)</li>
                            <li>Installation details assessment</li>
                            <li>Installer credibility review</li>
                            <li>Critical red flags (if any)</li>
                            <li>Things to consider before proceeding</li>
                            <li>Important questions to ask your installer</li>
                        </ul>
                        
                        <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                            <p style="margin: 0;"><strong>⚠️ Important:</strong> This report is for informational purposes only. Always conduct your own due diligence and consult with qualified professionals before making installation decisions.</p>
                        </div>
                        
                        <p>Need another analysis? Log in to your premium account at <a href="https://solarverify.co.uk" style="color: #0d9488;">solarverify.co.uk</a></p>
                        
                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                        
                        <p style="font-size: 12px; color: #6b7280; margin: 0;">
                            Questions or feedback? Reply to this email or contact us at justinburgher@solarverify.co.uk
                        </p>
                        <p style="font-size: 12px; color: #6b7280; margin: 5px 0 0 0;">
                            © {datetime.now().year} SolarVerify. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        
        # Attach PDF
        attachment = Attachment(
            FileContent(encoded_pdf),
            FileName(f'SolarVerify_Premium_Report_{datetime.now().strftime("%Y%m%d")}.pdf'),
            FileType('application/pdf'),
            Disposition('attachment')
        )
        message.attachment = attachment
        
        # Send email
        response = sendgrid_client.send(message)
        
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"Error sending premium report email: {str(e)}")
        return False
