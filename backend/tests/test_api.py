import json

from app.models.database import ProcessingStage, Swing, SwingAnalysis, SwingStatus

from tests.conftest import upload_fake_swing


class TestHealth:
    def test_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestUpload:
    def test_upload_accepts_mp4_and_enqueues(self, client, enqueued):
        swing_id = upload_fake_swing(client)
        assert enqueued == [swing_id]

        detail = client.get(f"/api/v1/swings/{swing_id}").json()
        assert detail["status"] == "queued"
        assert detail["original_filename"] == "swing.mp4"
        assert detail["handedness"] == "right"

    def test_upload_respects_handedness(self, client):
        response = client.post(
            "/api/v1/swings/upload",
            files={"file": ("s.mov", b"data", "video/quicktime")},
            data={"handedness": "left"},
        )
        assert response.status_code == 202
        detail = client.get(f"/api/v1/swings/{response.json()['id']}").json()
        assert detail["handedness"] == "left"

    def test_upload_rejects_unsupported_extension(self, client, enqueued):
        response = client.post(
            "/api/v1/swings/upload",
            files={"file": ("swing.gif", b"gifdata", "image/gif")},
        )
        assert response.status_code == 415
        assert enqueued == []

    def test_upload_rejects_empty_file(self, client):
        response = client.post(
            "/api/v1/swings/upload",
            files={"file": ("swing.mp4", b"", "video/mp4")},
        )
        assert response.status_code == 400

    def test_upload_rejects_oversized_file(self, client, test_app):
        test_app.state.settings.max_upload_mb = 0
        response = client.post(
            "/api/v1/swings/upload",
            files={"file": ("swing.mp4", b"x" * 2048, "video/mp4")},
        )
        assert response.status_code == 413


class TestSwingRetrieval:
    def test_list_orders_newest_first(self, client):
        first = upload_fake_swing(client, "one.mp4")
        second = upload_fake_swing(client, "two.mp4")
        listing = client.get("/api/v1/swings").json()
        ids = [s["id"] for s in listing]
        assert ids.index(second) < ids.index(first)

    def test_unknown_swing_404s(self, client):
        assert client.get("/api/v1/swings/nope").status_code == 404

    def test_detail_includes_analysis_when_complete(self, client, test_app):
        swing_id = upload_fake_swing(client)

        with test_app.state.session_factory() as session:
            swing = session.get(Swing, swing_id)
            swing.status = SwingStatus.COMPLETED
            swing.stage = ProcessingStage.DONE.value
            swing.progress = 100.0
            swing.analysis = SwingAnalysis(
                phases=[{"name": "address", "start_frame": 0, "end_frame": 10,
                         "start_time": 0.0, "end_time": 0.33}],
                metrics={"tempo_ratio": 3.1},
                coaching={"overall": "solid swing"},
            )
            session.commit()

        detail = client.get(f"/api/v1/swings/{swing_id}").json()
        assert detail["status"] == "completed"
        assert detail["phases"][0]["name"] == "address"
        assert detail["metrics"]["tempo_ratio"] == 3.1
        assert detail["coaching"]["overall"] == "solid swing"
        assert detail["video_urls"]["annotated"].endswith(f"/swings/{swing_id}/video/annotated")

    def test_artifacts_404_until_produced(self, client):
        swing_id = upload_fake_swing(client)
        # original was saved by the upload itself
        assert client.get(f"/api/v1/swings/{swing_id}/video/original").status_code == 200
        # but nothing has been processed
        assert client.get(f"/api/v1/swings/{swing_id}/video/annotated").status_code == 404
        assert client.get(f"/api/v1/swings/{swing_id}/keypoints").status_code == 404


class TestDelete:
    def test_delete_removes_swing_and_files(self, client, test_app):
        swing_id = upload_fake_swing(client)
        assert client.delete(f"/api/v1/swings/{swing_id}").status_code == 204
        assert client.get(f"/api/v1/swings/{swing_id}").status_code == 404
        assert not list(test_app.state.storage.swing_dir(swing_id).glob("original.*"))

    def test_delete_refuses_while_processing(self, client, test_app):
        swing_id = upload_fake_swing(client)
        with test_app.state.session_factory() as session:
            session.get(Swing, swing_id).status = SwingStatus.PROCESSING
            session.commit()
        assert client.delete(f"/api/v1/swings/{swing_id}").status_code == 409


class TestProgressWebSocket:
    def test_unknown_swing_closes_with_4404(self, client):
        with client.websocket_connect("/ws/swings/missing/progress") as ws:
            # server sends nothing and closes; receive() surfaces the close
            closed = ws.receive()
            assert closed["type"] == "websocket.close"
            assert closed["code"] == 4404

    def test_terminal_swing_gets_snapshot_then_close(self, client, test_app):
        swing_id = upload_fake_swing(client)
        with test_app.state.session_factory() as session:
            swing = session.get(Swing, swing_id)
            swing.status = SwingStatus.COMPLETED
            swing.progress = 100.0
            session.commit()

        with client.websocket_connect(f"/ws/swings/{swing_id}/progress") as ws:
            msg = json.loads(ws.receive_text())
            assert msg["status"] == "completed"
            assert msg["progress"] == 100.0

    def test_polling_fallback_streams_db_updates(self, client, test_app):
        swing_id = upload_fake_swing(client)

        with client.websocket_connect(f"/ws/swings/{swing_id}/progress") as ws:
            first = json.loads(ws.receive_text())
            assert first["status"] == "queued"

            with test_app.state.session_factory() as session:
                swing = session.get(Swing, swing_id)
                swing.status = SwingStatus.COMPLETED
                swing.stage = ProcessingStage.DONE.value
                swing.progress = 100.0
                session.commit()

            # redis is unreachable in tests, so this arrives via DB polling
            final = json.loads(ws.receive_text())
            assert final["status"] == "completed"
