from teal import enums


def test_enum_currency():
    assert enums.Currency.EGP.value == 31


def test_enum_continent():
    assert enums.Continent.AF.value == 'Africa'


def test_enum_country():
    assert enums.Country.PH.value == 'Philippines'


def test_enum_subdivision():
    assert enums.Subdivision['ES-CA'].value == 963


def test_enum_subdivision_in_country():
    assert enums.Subdivision['ES-CA'] in enums.Country.ES
    assert enums.Subdivision['ES-CA'] not in enums.Country.PH
