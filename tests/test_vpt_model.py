import pytest

from engine.vpt_model import (
    VptCompositeSection,
    VptConcreteSection,
    VptGeometry,
    VptLajeSide,
    VptPassiveLayer,
    VptPrestressLayer,
    VPT_SECTION_CATALOG,
    equivalent_prestress,
    passive_area_and_ys,
    taxa_passiva_longitudinal,
    taxa_passiva_total,
    taxa_passiva_transversal,
    taxa_protendida,
)


def _default_sections():
    left = VptLajeSide(lp_type="LP26,5", rev=200, acd=300, vao=9.6)
    right = VptLajeSide(lp_type="LP26,5", rev=200, acd=300, vao=6.6)
    geom = VptGeometry(bw=40, h1=25, h2=10, h3=15, hc=0, capa=5, b_capa=40, bf=52)
    derived = geom.derived(left.cap, right.cap)
    bottom_layers = (
        VptPassiveLayer(n_barras=2, diam_mm=25.0, ys=5),
        VptPassiveLayer(n_barras=2, diam_mm=20.0, ys=12),
        VptPassiveLayer(n_barras=0, diam_mm=32.0, ys=18),
    )
    top_layer = VptPassiveLayer(n_barras=2, diam_mm=12.5, ys=-4.425)
    as_bottom, ys = passive_area_and_ys(bottom_layers)
    concrete = VptConcreteSection(
        derived,
        as_inferior=as_bottom,
        ys=ys,
        as_superior=top_layer.area(),
        ys_superior=top_layer.ys,
        fat_i=5.303300858899107,
    )
    composite = VptCompositeSection(concrete, fck=50, fck_capa=40)
    return left, right, derived, concrete, composite


def test_vpt_laje_side_matches_planilha():
    left, right, *_ = _default_sections()

    assert left.pp == 370
    assert left.cap == 27
    assert left.be == 14
    assert left.capa_load(5) == 150
    assert right.pp == 370
    assert right.cap == 27
    assert right.be == 14


def test_vpt_section_catalog_from_spreadsheet():
    assert len(VPT_SECTION_CATALOG) == 39
    assert VPT_SECTION_CATALOG["T95/65x50"].bw == 50
    assert VPT_SECTION_CATALOG["T95/65x50"].h1 == 65
    assert VPT_SECTION_CATALOG["T95/65x50"].h2 == 10
    assert VPT_SECTION_CATALOG["T95/65x50"].h3 == 20
    assert VPT_SECTION_CATALOG["T95/65x50"].hp == 95
    assert VPT_SECTION_CATALOG["T45/25x30"].bw == 30
    assert VPT_SECTION_CATALOG["T45/25x30"].hp == 45


def test_vpt_geometry_matches_planilha_default():
    _, _, geom, _, _ = _default_sections()

    assert geom.h4 == 0
    assert geom.hp == 50
    assert geom.h == 82
    assert geom.hs == 27
    assert geom.he == 15
    assert geom.hd == 15
    assert geom.bs1 == 60
    assert geom.bs == 80


def test_vpt_concrete_section_matches_planilha_default():
    _, _, _, section, _ = _default_sections()
    areas = section.area_parts
    cgs = section.centroids

    assert areas["a0"] == 0
    assert areas["a1"] == 0
    assert areas["a2"] == 1200
    assert areas["a3"] == 600
    assert areas["a4"] == 1000
    assert section.ac == 2800
    assert cgs["cg0"] == 50
    assert cgs["cg1"] == 50
    assert cgs["cg2"] == 42.5
    assert cgs["cg3"] == pytest.approx(30.5555555556)
    assert cgs["cg4"] == 12.5
    assert section.cg == pytest.approx(28.7690162191)
    assert section.ix == pytest.approx(605888.8700165)
    assert section.ws == pytest.approx(28537.9554838)
    assert section.wi == pytest.approx(21060.4653771)
    assert section.pp_viga == pytest.approx(0.7)


def test_vpt_composite_section_matches_planilha_default():
    _, _, _, _, composite = _default_sections()

    assert composite.b_capa_eq == pytest.approx(34.8101393254)
    assert composite.bf_eq == pytest.approx(45.2531811230)
    assert composite.ac_f == pytest.approx(4195.8865869486)
    assert composite.cg_f == pytest.approx(40.9870122242)
    assert composite.ix_f == pytest.approx(1975889.8626448)
    assert composite.ws_f == pytest.approx(48177.1743489754)
    assert composite.ws_f1 == pytest.approx(219226.9546798445)
    assert composite.wi_f == pytest.approx(48207.7066714288)


def test_vpt_prestress_layers_match_planilha_default():
    layers = (
        VptPrestressLayer(n_cord=6, diam_mm=12.7),
        VptPrestressLayer(n_cord=3, diam_mm=12.7),
        VptPrestressLayer(n_cord=0, diam_mm=15.2),
    )

    n_cord, yp, asp = equivalent_prestress(layers, cob=3)

    assert n_cord == 9
    assert yp == pytest.approx(5.9683333333)
    assert asp == pytest.approx(8.91)


def test_vpt_passive_layers_and_rates_match_planilha_default():
    _, _, geom, section, _ = _default_sections()
    bottom_layers = (
        VptPassiveLayer(n_barras=2, diam_mm=25.0, ys=5),
        VptPassiveLayer(n_barras=2, diam_mm=20.0, ys=12),
        VptPassiveLayer(n_barras=0, diam_mm=32.0, ys=18),
    )
    top_layer = VptPassiveLayer(n_barras=2, diam_mm=12.5, ys=-4.425)

    as_bottom, ys = passive_area_and_ys(bottom_layers)
    as_top = top_layer.area()
    tx_long = taxa_passiva_longitudinal(as_bottom, as_top, geom.h, section.ac)
    tx_trans = taxa_passiva_transversal(asw=6.514602279827775, geom=geom, ac=section.ac)
    tx_total = taxa_passiva_total(as_bottom, as_top, 6.514602279827775, geom, section.ac)

    assert as_bottom == pytest.approx(16.1006623496)
    assert ys == pytest.approx(7.7317073171)
    assert as_top == pytest.approx(2.4543692606)
    assert tx_long == pytest.approx(75.0096421931)
    assert tx_trans == pytest.approx(39.9736469966)
    assert tx_total == pytest.approx(114.9832891897)


def test_vpt_prestress_rate_matches_planilha_default():
    _, _, _, section, _ = _default_sections()
    _, _, asp = equivalent_prestress(
        (
            VptPrestressLayer(n_cord=6, diam_mm=12.7),
            VptPrestressLayer(n_cord=3, diam_mm=12.7),
            VptPrestressLayer(n_cord=0, diam_mm=15.2),
        ),
        cob=3,
    )

    assert taxa_protendida(asp, section.ac) == pytest.approx(24.8843571429)
