-- PostgreSQL Migration for Sales Returns / Credit Notes
-- Adds voucher_id to payment_allocations to allow linking a credit note voucher to an invoice

ALTER TABLE payment_allocations 
ADD COLUMN voucher_id INTEGER;

ALTER TABLE payment_allocations 
ADD CONSTRAINT fk_payment_allocations_vouchers 
FOREIGN KEY (voucher_id) 
REFERENCES vouchers (id) 
ON DELETE CASCADE;
