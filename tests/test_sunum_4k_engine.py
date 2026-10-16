import pytest
import re
from app import app, _prepare_advanced_listing_data, _listings_cache

def test_prepare_advanced_listing_data():
    sample_listing = {
        "id": "test-123",
        "title": "Çankaya Gaziosmanpaşa Lüks Satılık Ofis",
        "price": "₺45.000.000",
        "loc": "Çankaya, Ankara",
        "type": "Satılık",
        "rooms": "4+1",
        "area": "280 m2",
        "img": "https://media.cb.com.tr/StockMediaFiles/5581/DSCF9687_2X26IZP6QD_331X224.jpg",
        "link": "https://www.cb.com.tr/ankara-cankaya-cankaya-kiralik/ofis/373541"
    }
    data = _prepare_advanced_listing_data(sample_listing)
    assert data["title"] == sample_listing["title"]
    assert data["price"] == sample_listing["price"]
    assert data["img"].endswith(".jpg")
    # Verify thumbnail size tag was stripped to master high-res
    assert "_331X224" not in data["img"]
    assert len(data["images"]) > 0
    assert "slogan" in data
    assert "agent" in data
    assert data["agent"]["name"] == "YİĞİT NARİN"

def test_image_proxy_endpoint():
    with app.test_client() as client:
        # Test missing param
        res = client.get("/api/image-proxy")
        assert res.status_code == 400

        # Test invalid url
        res = client.get("/api/image-proxy?url=invalid-url")
        assert res.status_code == 400

        # Test valid thumbnail url upgrade
        test_url = "https://media.cb.com.tr/StockMediaFiles/5628/100_VLOPYOZ83X_331X224.jpg"
        res = client.get(f"/api/image-proxy?url={test_url}")
        assert res.status_code == 200
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
        assert "image/" in res.headers.get("Content-Type", "")
        # High res image should be substantially larger than 19KB thumbnail
        assert len(res.data) > 50000

def test_sunum_advanced_route():
    with app.test_client() as client:
        # Ensure listings cache has at least 1 item
        if not _listings_cache.get("data"):
            _listings_cache["data"] = [{
                "id": "sample-01",
                "title": "Kızılcaşar Ticari Satılık Bina",
                "price": "₺78.249.000",
                "loc": "Gölbaşı, Ankara",
                "type": "Satılık",
                "img": "https://media.cb.com.tr/StockMediaFiles/5628/100_VLOPYOZ83X_331X224.jpg"
            }]
        res = client.get("/sunum/advanced/0")
        assert res.status_code == 200
        html = res.data.decode("utf-8")
        assert "4K Ultra HD" in html
        assert "YİĞİT NARİN" in html
        assert "Coldwell Banker" in html
        assert "generate4KExport" in html
        assert "api/image-proxy" in html
