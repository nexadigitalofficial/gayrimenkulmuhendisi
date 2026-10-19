import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

def test_nexa_cloud_api_key_support():
    from app import PAGESPEED_API_KEY
    assert PAGESPEED_API_KEY is not None
    assert len(PAGESPEED_API_KEY) > 10

def test_job_disk_state_persistence(tmp_path):
    from app import Job, JOBS_DIR
    import app
    
    # Override JOBS_DIR temporarily
    orig_jobs_dir = app.JOBS_DIR
    app.JOBS_DIR = tmp_path
    try:
        job = Job("test_job_123", "sahibinden", {"url": "https://example.com"})
        job.logs.append("Test log entry 1\n")
        job.set_step(0)
        
        status_file = tmp_path / "test_job_123" / "status.json"
        assert status_file.exists()
        
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["status"] == "queued"
            assert data["step_index"] == 0
            assert "Test log entry 1" in data["all_logs"]
    finally:
        app.JOBS_DIR = orig_jobs_dir

def test_route_status_disk_fallback(tmp_path):
    from app import app as flask_app
    import app
    
    orig_base = app.BASE_DIR
    app.BASE_DIR = tmp_path
    jobs_dir = tmp_path / "jobs" / "disk_only_job"
    jobs_dir.mkdir(parents=True)
    
    status_data = {
        "status": "done",
        "job_type": "sahibinden",
        "step_index": 5,
        "step_label": "Tamamlandı",
        "step_total": 6,
        "total_listings": 8,
        "error": "",
        "output_ready": True,
        "output_url": "/jobs/disk_only_job/ilan_detay_karti.html",
        "all_logs": "Line 1\nLine 2\n",
        "new_logs": "Line 1\nLine 2\n",
        "log_len": 14,
        "elapsed": 12.5
    }
    with open(jobs_dir / "status.json", "w", encoding="utf-8") as f:
        json.dump(status_data, f)
        
    try:
        with flask_app.test_client() as client:
            resp = client.get("/api/status/disk_only_job?after=0")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "done"
            assert data["total_listings"] == 8
            assert "Line 1" in data["new_logs"]
    finally:
        app.BASE_DIR = orig_base

def test_cloud_dom_branding_in_luxury_cards():
    from app import build_luxury_cards_page, build_luxury_card_html
    sample_detail = {
        "listing_id": "123456",
        "title": "Lüks Villa",
        "price": "25.000.000 TL",
        "photos": ["https://example.com/photo.jpg"],
        "raw_description": "Harika konumda villa",
    }
    html_single = build_luxury_card_html(sample_detail)
    assert "PageSpeed" not in html_single
    assert "NEXA" in html_single

    html_multi = build_luxury_cards_page([sample_detail, {**sample_detail, "listing_id": "654321"}])
    assert "PageSpeed" not in html_multi
    assert "NEXA" in html_multi
