import pytest

from informes_warrants import config
from informes_warrants.config import ConfiguracionError, configurar_identidad


@pytest.fixture(autouse=True)
def sin_dotenv(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)


def test_falla_sin_identidad(monkeypatch):
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
    with pytest.raises(ConfiguracionError):
        configurar_identidad()


def test_falla_sin_email(monkeypatch):
    monkeypatch.setenv("EDGAR_IDENTITY", "Solo Nombre")
    with pytest.raises(ConfiguracionError):
        configurar_identidad()


def test_acepta_identidad_valida(monkeypatch):
    monkeypatch.setenv("EDGAR_IDENTITY", "Ana Prueba ana@example.com")
    assert configurar_identidad() == "Ana Prueba ana@example.com"


def test_directorio_datos_fuera_de_onedrive(monkeypatch, tmp_path):
    monkeypatch.setenv("INFORMES_DATA_DIR", str(tmp_path / "datos"))
    assert config.directorio_datos() == tmp_path / "datos"
    monkeypatch.setenv("INFORMES_DATA_DIR", str(tmp_path / "OneDrive" / "datos"))
    with pytest.raises(ConfiguracionError, match="OneDrive"):
        config.directorio_datos()
