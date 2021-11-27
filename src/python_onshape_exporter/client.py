from base64 import b64encode
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qsl
from secrets import token_urlsafe

import aiohttp
import hashlib
import hmac


class Onshape:
    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key

        self.session = aiohttp.ClientSession()

    def __generate_hmac(self, hmac_str):
        return hmac.new(
            self.secret_key.encode(), hmac_str, digestmod=hashlib.sha256
        ).digest()

    def sign_request(self, method, path, query, headers):
        query = urlencode(query)
        nonce = token_urlsafe(25)
        method = method.lower()
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        hmac = b64encode(
            self.__generate_hmac(
                f"{method}\n{nonce}\n{date}\n{headers['Content-Type']}\n{path}\n{query}\n".lower().encode()
            )
        )

        headers["Date"] = date
        headers["On-Nonce"] = nonce
        headers["Authorization"] = f"On {self.access_key}:HmacSHA256:{hmac.decode()}"

    async def __call(
        self,
        method,
        path,
        headers=None,
        query=None,
        json=None,
        base_url="https://cad.onshape.com",
    ):
        if not headers:
            headers = {}
        headers["Content-Type"] = "application/json"
        self.sign_request(method, path, query, headers)

        async with getattr(self.session, method.lower())(
            url=base_url + path,
            json=json,
            headers=headers,
            params=query,
            allow_redirects=False,
        ) as resp:
            if resp.status == 200 and resp.content_type == "application/json":
                response_data = await resp.json()
                return response_data
            elif resp.status == 307:
                url = urlparse(resp.headers["Location"])
                query = dict(parse_qsl(url.query))
                return await self.__call(
                    "get",
                    url.path,
                    query=query,
                    base_url=f"{url.scheme}://{url.netloc}",
                )
            else:
                return await resp.read()

    async def get_assembly_bom(self, did, wid, eid):
        return await self.__call(
            "get",
            f"/api/assemblies/d/{did}/w/{wid}/e/{eid}/bom",
            query={
                "generateIfAbsent": "true",
                "multiLevel": "true",
                "indented": "false",
            },
        )

    async def export_part(self, did, wvm_id, wvm_type, eid, part_id, configuration):
        return await self.__call(
            "get",
            f"/api/partstudios/d/{did}/{wvm_type}/{wvm_id}/e/{eid}/stl",
            query={
                "mode": "binary",
                "partIds": part_id,
                "grouping": "false",
                "units": "millimeter",
                "configuration": configuration,
            },
        )

    async def get_shaded_view(self, did, wid, eid, height=1200, width=850):
        return await self.__call(
            "get",
            f"/api/assemblies/d/{did}/w/{wid}/e/{eid}/shadedviews",
            query={
                "viewMatrix": "trimetric",
                "outputHeight": height,
                "outputWidth": width,
                "showAllParts": "true",
                "useAntiAliasing": "true",
                "pixelSize": 0,
            },
        )

    async def close(self):
        await self.session.close()

    async def __aenter__(self) -> aiohttp.ClientSession:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        await self.close()
