import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { Capacitor } from '@capacitor/core';

export async function generateAndShareInvoice(invoice: any, party: any) {
  const doc = new jsPDF();
  
  // Header
  doc.setFontSize(20);
  doc.text('TAX INVOICE', 105, 20, { align: 'center' });

  // Company Info
  doc.setFontSize(10);
  doc.text('Maxwell Accounting', 14, 30);
  doc.text('123 Business Road, City', 14, 35);

  // Invoice Info
  doc.text(`Invoice No: ${invoice.invoice_number}`, 140, 30);
  doc.text(`Date: ${new Date(invoice.invoice_date).toLocaleDateString()}`, 140, 35);
  if (invoice.due_date) {
    doc.text(`Due Date: ${new Date(invoice.due_date).toLocaleDateString()}`, 140, 40);
  }

  // Party Info
  doc.text('Billed To:', 14, 50);
  doc.setFont('', 'bold');
  doc.text(party?.name || 'Unknown Party', 14, 55);
  doc.setFont('', 'normal');
  doc.text(`Agent: ${party?.agent_name || '-'}`, 14, 60);

  // Billing & Shipping Address
  doc.text('Billing Address:', 14, 70);
  const billLines = invoice.billing_address ? invoice.billing_address.split(',') : ['-'];
  doc.text(billLines, 14, 75);

  doc.text('Shipping Address:', 105, 70);
  const shipLines = invoice.shipping_address ? invoice.shipping_address.split(',') : ['-'];
  doc.text(shipLines, 105, 75);

  // Items Table
  const tableData = (invoice.items || []).map((item: any) => [
    item.item_name,
    item.meter,
    `Rs. ${item.rate}`,
    `Rs. ${item.total}`
  ]);

  autoTable(doc, {
    startY: 95,
    head: [['Item Name', 'Meter / Qty', 'Rate', 'Total Amount']],
    body: tableData,
    foot: [['', '', 'Grand Total:', `Rs. ${invoice.amount}`]],
    theme: 'grid',
    headStyles: { fillColor: [234, 179, 8] },
    footStyles: { fillColor: [240, 240, 240], textColor: [0, 0, 0] },
  });

  // Export PDF
  const pdfOutput = doc.output('datauristring');
  const base64Data = pdfOutput.split(',')[1];
  const fileName = `Invoice_${invoice.invoice_number}.pdf`;

  if (Capacitor.isNativePlatform()) {
    try {
      const savedFile = await Filesystem.writeFile({
        path: fileName,
        data: base64Data,
        directory: Directory.Cache
      });

      await Share.share({
        title: 'Invoice',
        text: `Here is your invoice ${invoice.invoice_number} from Maxwell Accounting.`,
        url: savedFile.uri,
        dialogTitle: 'Share Invoice'
      });
    } catch (err) {
      console.error('Error sharing PDF', err);
      alert('Error sharing PDF on device');
    }
  } else {
    // Web fallback: Open preview in new tab
    const blobUrl = doc.output('bloburl');
    window.open(blobUrl, '_blank');
  }
}

// ── Party Statement PDF ───────────────────────────────────────────────────────

export async function generateAndSharePartyStatement(party: any, unpaidInvoices: any[], unallocatedBalance: number = 0) {
  const doc = new jsPDF();
  const today = new Date().toLocaleDateString('en-IN');

  // Header
  doc.setFontSize(18);
  doc.text('OUTSTANDING STATEMENT', 105, 18, { align: 'center' });

  doc.setFontSize(10);
  doc.text('Maxwell Accounting', 14, 28);
  doc.text(`Date: ${today}`, 140, 28);

  // Party info
  doc.setDrawColor(108, 99, 255);
  doc.setLineWidth(0.5);
  doc.line(14, 34, 196, 34);

  doc.setFontSize(11);
  doc.setFont('', 'bold');
  doc.text(party.name || '', 14, 42);
  doc.setFont('', 'normal');
  doc.setFontSize(9);
  if (party.phone) doc.text(`Phone: ${party.phone}`, 14, 47);
  if (party.billing_city) doc.text(`City: ${party.billing_city}`, 14, 52);
  if (party.agent_name) doc.text(`Agent: ${party.agent_name}`, 14, 57);

  // Unpaid invoices table
  const rows = unpaidInvoices.map((inv: any) => [
    inv.invoice_number,
    new Date(inv.invoice_date).toLocaleDateString('en-IN'),
    inv.due_date ? new Date(inv.due_date).toLocaleDateString('en-IN') : '-',
    `Rs. ${Number(inv.amount).toFixed(2)}`,
    `Rs. ${Number(inv.balance_due).toFixed(2)}`,
  ]);

  const totalOutstanding = unpaidInvoices.reduce((s: number, i: any) => s + Number(i.balance_due), 0);
  const netPayable = totalOutstanding - unallocatedBalance;

  let foot = [];
  if (unallocatedBalance > 0) {
    foot = [
      ['', '', '', 'Total Invoices Due:', `Rs. ${totalOutstanding.toFixed(2)}`],
      ['', '', '', 'On Account / Advance:', `Rs. ${unallocatedBalance.toFixed(2)}`],
      ['', '', '', 'Net Payable:', `Rs. ${netPayable.toFixed(2)}`]
    ];
  } else {
    foot = [['', '', '', 'Total Outstanding:', `Rs. ${totalOutstanding.toFixed(2)}`]];
  }

  autoTable(doc, {
    startY: 65,
    head: [['Invoice No.', 'Invoice Date', 'Due Date', 'Amount', 'Balance Due']],
    body: rows,
    foot: foot,
    theme: 'striped',
    headStyles: { fillColor: [234, 179, 8] },
    footStyles: { fillColor: [250, 250, 250], textColor: [0, 0, 0], fontStyle: 'bold' },
    columnStyles: { 4: { fontStyle: 'bold' } },
  });

  const fileName = `Statement_${party.name?.replace(/\s+/g, '_')}_${today.replace(/\//g, '-')}.pdf`;
  const pdfOutput = doc.output('datauristring');
  const base64Data = pdfOutput.split(',')[1];

  if (Capacitor.isNativePlatform()) {
    try {
      const savedFile = await Filesystem.writeFile({
        path: fileName,
        data: base64Data,
        directory: Directory.Cache,
      });

      await Share.share({
        title: `Statement — ${party.name}`,
        text: `Outstanding statement for ${party.name} as of ${today}.\nNet Payable: Rs. ${netPayable.toFixed(2)}`,
        url: savedFile.uri,
        dialogTitle: 'Share Statement',
      });
    } catch (err) {
      console.error('Error sharing statement', err);
      alert('Error sharing PDF on device');
    }
  } else {
    // Web fallback: Open preview in new tab
    const blobUrl = doc.output('bloburl');
    window.open(blobUrl, '_blank');
  }
}

// ── WhatsApp direct open ──────────────────────────────────────────────────────

export function openWhatsApp(phone: string, message = '') {
  // Normalize: strip spaces/dashes, prepend +91 if no country code
  let num = phone.replace(/[\s\-().]/g, '');
  if (!num.startsWith('+')) {
    num = '+91' + num.replace(/^0/, '');
  }
  const url = `https://wa.me/${num.replace('+', '')}${message ? `?text=${encodeURIComponent(message)}` : ''}`;
  window.open(url, '_blank');
}


// ── F11: Payment Receipt PDF ──────────────────────────────────────────────────

export async function generateAndSharePaymentReceipt(payment: any, party: any) {
  const doc = new jsPDF();
  const today = new Date(payment.payment_date).toLocaleDateString('en-IN');
  const receiptNo = `PMT-${String(payment.id).padStart(4, '0')}`;
  const modeLabel = (payment.mode || 'cash').toUpperCase();

  // Header
  doc.setFontSize(20);
  doc.text('PAYMENT RECEIPT', 105, 20, { align: 'center' });

  doc.setFontSize(10);
  doc.text('Maxwell Accounting', 14, 30);
  doc.text(`Receipt No: ${receiptNo}`, 140, 30);
  doc.text(`Date: ${today}`, 140, 35);
  doc.text(`Mode: ${modeLabel}`, 140, 40);

  // Divider
  doc.setDrawColor(234, 179, 8);
  doc.setLineWidth(0.5);
  doc.line(14, 46, 196, 46);

  // Party info
  doc.setFontSize(11);
  doc.setFont('', 'bold');
  doc.text('Received From:', 14, 55);
  doc.setFont('', 'normal');
  doc.setFontSize(10);
  doc.text(party?.name || 'Unknown Party', 14, 61);
  if (party?.phone) doc.text(`Phone: ${party.phone}`, 14, 66);
  if (party?.billing_city) doc.text(`City: ${party.billing_city}`, 14, 71);

  // Amount box
  doc.setFillColor(234, 179, 8);
  doc.roundedRect(14, 80, 182, 24, 4, 4, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(12);
  doc.text('Amount Received:', 20, 91);
  doc.setFontSize(18);
  doc.setFont('', 'bold');
  doc.text(`Rs. ${Number(payment.amount).toFixed(2)}`, 196, 91, { align: 'right' });
  doc.setTextColor(0, 0, 0);
  doc.setFont('', 'normal');

  // Note
  if (payment.note) {
    doc.setFontSize(10);
    doc.text(`Note: ${payment.note}`, 14, 115);
  }

  // Allocations
  if (payment.allocations && payment.allocations.length > 0) {
    autoTable(doc, {
      startY: 122,
      head: [['Invoice No.', 'Amount Applied']],
      body: payment.allocations.map((a: any) => [
        a.invoice_number,
        `Rs. ${Number(a.allocated_amount).toFixed(2)}`,
      ]),
      ...(payment.unallocated > 0
        ? { foot: [['On Account / Advance', `Rs. ${Number(payment.unallocated).toFixed(2)}`]] }
        : {}),
      theme: 'grid',
      headStyles: { fillColor: [234, 179, 8] },
      footStyles: { fillColor: [250, 250, 250], textColor: [0, 0, 0], fontStyle: 'bold' },
    });
  } else if (Number(payment.unallocated) > 0) {
    doc.setFontSize(10);
    doc.text(`On Account / Advance: Rs. ${Number(payment.unallocated).toFixed(2)}`, 14, 122);
  }

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(150, 150, 150);
  doc.text('This is a computer-generated receipt. No signature required.', 105, 285, { align: 'center' });

  const fileName = `Receipt_${receiptNo}_${party?.name?.replace(/\s+/g, '_') || 'party'}.pdf`;
  const pdfOutput = doc.output('datauristring');
  const base64Data = pdfOutput.split(',')[1];

  if (Capacitor.isNativePlatform()) {
    try {
      const savedFile = await Filesystem.writeFile({
        path: fileName,
        data: base64Data,
        directory: Directory.Cache,
      });
      await Share.share({
        title: `Payment Receipt — ${party?.name}`,
        text: `Payment receipt ${receiptNo} for Rs. ${Number(payment.amount).toFixed(2)} from ${party?.name}.`,
        url: savedFile.uri,
        dialogTitle: 'Share Receipt',
      });
    } catch (err) {
      console.error('Error sharing receipt', err);
      alert('Error sharing receipt on device');
    }
  } else {
    // Web fallback: Open preview in new tab
    const blobUrl = doc.output('bloburl');
    window.open(blobUrl, '_blank');
  }
}
