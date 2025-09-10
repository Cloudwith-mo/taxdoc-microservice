import decimal
D = decimal.Decimal

def validate_bank_statement(doc):
    errors = []
    if not doc.get('truncated'):
        try:
            beg = D(doc['balances']['beginning'])
            end = D(doc['balances']['ending'])
            deb = D(doc['balances'].get('total_debits','0.00'))
            cre = D(doc['balances'].get('total_credits','0.00'))
            if (beg + cre - deb).quantize(D('0.01')) != D(end).quantize(D('0.01')):
                errors.append('Math check failed: beginning + credits - debits != ending')
        except Exception as e:
            errors.append(f'Balance parse error: {e}')
    # basic date sanity
    s = doc['statement_period']['start']
    e = doc['statement_period']['end']
    if s > e:
        errors.append('statement_period.start after end')
    return errors