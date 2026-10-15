from tabacos.discover import candidates, month_of

BASE = "https://www.hacienda.gob.es/tabacos/informes%20comite%20consultivo/"


def test_candidates_cover_every_filename_style_seen_in_2021_2026():
    c = set(candidates(2024, 5))      # published as informe-mercado.mayo24.pdf
    assert BASE + "informes2024/informe-mercado.mayo24.pdf" in c
    c = set(candidates(2025, 6))      # published as IINFORMES2025/Informe-junio2025.pdf
    assert BASE + "iinformes2025/informe-junio2025.pdf" in c
    assert BASE + "informes2026/informe-mercado-marzo26.pdf" in set(candidates(2026, 3))


def test_month_of_reads_the_month_from_a_filename():
    assert month_of("informe-mercado-septiembre2022.pdf") == 9
    assert month_of("informemercadonoviembre23.pdf") == 11
    assert month_of("3.1.%20informe%20de%20mercado122020.pdf") is None
