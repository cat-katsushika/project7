import secrets
import string
import uuid
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .utils import get_frontend_url


class Memo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    memo = models.TextField()
    passkey = models.CharField(unique=True, max_length=6)
    qr_img = models.ImageField(upload_to="qr_codes/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Memo {self.id}"

    def save(self, *args, **kwargs) -> None:
        # 通常のsaveを先に呼び出してidを生成
        if not self.id:
            super().save(*args, **kwargs)

        # インスタンスのidを含むURLを生成
        full_url = get_frontend_url(self.id)  # 自身のIDを含むURLを生成

        # URLからQRコードを生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        # 生成したQRコードを画像に変換
        img = qr.make_image(fill="black", back_color="white")

        # 画像を一時メモリに保存
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_content = ContentFile(img_io.getvalue(), "qr_code.png")

        # ImageFieldに画像をインスタンスのIDに基づいたファイル名で保存
        self.qr_img.save(f"{self.id}.png", img_content, save=False)

        # 再度saveを呼び出してQRコードを保存
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        # passkeyが6文字であることを確認
        passkey_length = 6
        if len(self.passkey) != passkey_length:
            msg = "Passkey must be 6 characters long"
            raise ValueError(msg)


@receiver(pre_save, sender=Memo)
def generate_passkey(sender, instance, **kwargs) -> None:  # noqa: ARG001
    # ランダムに6文字生成
    while True:
        characters = string.ascii_lowercase + string.digits
        passkey = "".join(secrets.choice(characters) for _ in range(6))
        # 重複していなければ採用
        if not Memo.objects.filter(passkey=passkey).exists():
            instance.passkey = passkey
            break


@receiver(post_delete, sender=Memo)
def delete_image_files(sender, instance, **kwargs) -> None:  # noqa: ARG001
    if instance.qr_img:
        instance.qr_img.delete(save=False)
