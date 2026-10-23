from receipted.extract import mask_card_numbers


def test_card_numbers_are_masked_but_prices_and_codes_are_not():
    assert mask_card_numbers("VISA 4111 1111 1111 1111 APPROVED") == "VISA [card ****1111] APPROVED"
    assert mask_card_numbers("CARD 5500-0000-0000-0004") == "CARD [card ****0004]"
    assert mask_card_numbers("1 NASI GORENG 25,000") == "1 NASI GORENG 25,000"
    assert mask_card_numbers("Plu# 10043 ACTAL TABLET 4.80") == "Plu# 10043 ACTAL TABLET 4.80"
    assert mask_card_numbers("GST Reg: M2-0077257-1") == "GST Reg: M2-0077257-1"
