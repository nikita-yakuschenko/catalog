# -*- coding: utf-8 -*-
import pytest

from app.services.parser import parse_characteristics, short_name_from_title, slugify


@pytest.mark.parametrize(
    'text,area',
    [
        ('Модульный дом площадью 89,9 м2', 89.9),
        ('Дом площадью 128,4 м²', 128.4),
        ('Площадь 75.88 м²', 75.88),
        ('площадью 123,1 м<sup>2</sup>', 123.1),
    ],
)
def test_parse_area(text, area):
    assert parse_characteristics(text).area == area


@pytest.mark.parametrize(
    'text,width,depth',
    [
        ('Размеры: 14,6х8,2 м', 14.6, 8.2),
        ('Размеры дома: 15х13,55 м', 15.0, 13.55),
        ('15,0×10,2 м', 15.0, 10.2),
        ('16.5x8.5', 16.5, 8.5),
    ],
)
def test_parse_dimensions(text, width, depth):
    parsed = parse_characteristics(text)
    assert parsed.width == width
    assert parsed.depth == depth
    assert parsed.dimensions_display is not None


def test_parse_rooms():
    text = 'Кол-во спален: 3\nКол-во с/у: 1-2'
    parsed = parse_characteristics(text)
    assert parsed.bedrooms == 3
    assert parsed.bathrooms == '1-2'


def test_short_name_and_slug():
    assert short_name_from_title('Модульный дом Барнхаус 90') == 'Барнхаус 90'
    assert 'barnhaus' in slugify('Барнхаус 90')
