def validate_1099_nec(doc):
    errors = []
    if not isinstance(doc.get('tax_year'), int):
        errors.append('tax_year must be integer')
    boxes = doc.get('boxes',{})
    if '1_nonemployee_comp' not in boxes:
        errors.append('missing box 1 nonemployee comp')
    return errors