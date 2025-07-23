from gcloud.aio.storage import Storage
from config import FIREBASE_CREDENTIALS_PATH
import base64


class StorageHandler:
    def __init__(self):
        self.bucket_name = self._get_bucket_name_from_credentials()
        self.storage = Storage(service_file=FIREBASE_CREDENTIALS_PATH)
    
    def _get_bucket_name_from_credentials(self):
        import json
        with open(FIREBASE_CREDENTIALS_PATH) as f:
            credentials = json.load(f)
        project_id = credentials['project_id']
        return f"{project_id}.appspot.com"

    async def upload_image(self, path, data):
        image_data = base64.b64decode(data)

        await self.storage.upload(
            bucket=self.bucket_name,
            object_name=path,
            file_data=image_data,
            content_type="image/jpeg"
        )

    async def delete_images(self, device_id):
        prefix = f"images/{device_id}/"
        params = {"prefix": prefix}

        data = await self.storage.list_objects(
                bucket=self.bucket_name,
                params=params
            )

        if "items" in data:
            for item in data["items"]:
                if "name" in item:
                    # Delete each image
                    await self.storage.delete(
                        bucket=self.bucket_name,
                        object_name=item["name"]
                    )


            