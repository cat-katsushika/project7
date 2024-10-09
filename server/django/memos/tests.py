import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Memo


class MemoAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.memo_url = reverse("memos:detail_with_passkey")

    def create_memo(self, memo_text="Test Memo"):
        memo = Memo.objects.create(memo=memo_text)
        memo.save()
        return memo

    def test_successful_post_request(self) -> None:
        # メモの作成
        memo_data = {"memo": "テスト用メモ"}
        memo = self.create_memo(memo_data["memo"])
        passkey = memo.passkey

        # タイムゾーン付きのローカル時間に変換してから ISO 形式に
        created_at = timezone.localtime(memo.created_at).isoformat()

        # 作成したメモの取得
        response = self.client.post(self.memo_url, data={"passkey": passkey})

        # Extract the path from the absolute URL
        response_path = urlparse(response.data["qr_img"]).path

        # レスポンスの確認
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(memo.id)
        assert response.data["memo"] == memo_data["memo"]
        assert response_path == memo.qr_img.url
        assert response.data["passkey"] == passkey
        assert response.data["created_at"] == created_at

    def test_failed_post_with_invalid_passkey(self) -> None:
        # 無効なパスキーでのリクエスト
        invalid_passkey = "invalid_passkey"
        response = self.client.post(self.memo_url, data={"passkey": invalid_passkey})

        # 失敗時のレスポンスの確認
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in response.data
        assert response.data["detail"] == "No Memo matches the given query."

    def test_failed_post_with_missing_passkey(self) -> None:
        # パスキーがない場合のリクエスト
        response = self.client.post(self.memo_url, data={})

        # 失敗時のレスポンスの確認
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data
        assert response.data["detail"] == "passkeyをリクエストボディに含めてください。"


class DeleteExpiredMemosAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.url = reverse("memos:delete_expired_memos")

    def create_memo(self, memo_text="Test Memo", created_at: timezone.datetime | None = None) -> Memo:
        if created_at is None:
            created_at = timezone.now()
        memo = Memo.objects.create(memo=memo_text)
        memo.save()
        memo.created_at = created_at
        memo.save()
        return memo

    def test_success_delete(self) -> None:
        # テストデータ作成
        self.create_memo()
        self.create_memo(created_at=timezone.now() - timezone.timedelta(minutes=settings.MEMO_LIFETIME_MINUTES + 1))

        # メモの数を取得
        memo_count = Memo.objects.count()
        expired_memo_count = Memo.objects.filter(
            created_at__lt=timezone.now() - timezone.timedelta(minutes=settings.MEMO_LIFETIME_MINUTES)
        ).count()

        res = self.client.delete(self.url)
        assert res.status_code == status.HTTP_200_OK
        assert Memo.objects.count() == memo_count - expired_memo_count
        assert res.data["detail"] == f"{expired_memo_count}個のmemoを削除しました。"


class MemoRetrieveDestroyAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.memo = Memo.objects.create(
            memo="だからしかしながら実人にしのはちょっと低級と得るなけれので、その陰をは立ちなけれどもという教場にもつばみなた。"
        )

    def setUp(self) -> None:
        self.url = reverse("memos:retrieve_destroy", kwargs={"pk": self.memo.pk})

    def test_success_get(self) -> None:
        res = self.client.get(self.url)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == str(Memo.objects.get(pk=self.memo.pk).id)

    def test_failure_get_with_not_exist_memo(self) -> None:
        res = self.client.get(reverse("memos:retrieve_destroy", kwargs={"pk": uuid.uuid4()}))
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert res.data["detail"] == "No Memo matches the given query."

    def test_success_delete(self) -> None:
        res = self.client.delete(self.url)
        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not Memo.objects.filter(pk=self.memo.pk).exists()
        assert res.data["detail"] == "メモを削除しました。"

    def test_failure_delete_with_not_exist_memo(self) -> None:
        res = self.client.delete(reverse("memos:retrieve_destroy", kwargs={"pk": uuid.uuid4()}))
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert res.data["detail"] == "No Memo matches the given query."


class MemoCreateAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.url = reverse("memos:create")

    def test_success_post(self) -> None:
        valid_data = {"memo": "その陰をは立ちなけれどもという教場にもつばみなた。"}
        res = self.client.post(self.url, valid_data, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert Memo.objects.filter(**valid_data).exists()

    def test_failure_post_with_empty_memo(self) -> None:
        invalid_data = {"memo": ""}
        res = self.client.post(self.url, invalid_data, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not Memo.objects.filter(**invalid_data).exists()
        assert res.data["memo"][0] == "この項目は空にできません。"
