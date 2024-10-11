from rest_framework import serializers

from .models import Memo


class MemoSerializer(serializers.ModelSerializer):
    qr_img = serializers.SerializerMethodField()

    class Meta:
        model = Memo
        fields = "__all__"
        read_only_fields = ("id", "qr_img", "passkey", "created_at")

    def get_qr_img(self, obj):
        """QRコード画像をHTTP URL に変換して返す."""
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.qr_img.url)
        msg = "Request object is required to build the absolute URI for 'qr_img'."
        raise RuntimeError(msg)
