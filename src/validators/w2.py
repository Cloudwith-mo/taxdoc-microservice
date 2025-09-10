def validate_w2(doc):
    errors = []
    # minimal required checks
    if not isinstance(doc.get('tax_year'), int):
        errors.append('tax_year must be integer')
    ein = (doc.get('employer',{}) or {}).get('ein','')
    if not ein:
        errors.append('missing employer EIN')
    ssn = (doc.get('employee',{}) or {}).get('ssn','')
    if not ssn:
        errors.append('missing employee SSN')
    return errors