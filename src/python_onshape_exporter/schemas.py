from typing import List
from pydantic import BaseModel


class ItemSource(BaseModel):
    configuration: str
    did: str
    eid: str
    wvm_type: str
    wvm_id: str
    part_id: str


class BOMItem(BaseModel):
    name: str
    description: str
    material: str
    quantity: float
    source: ItemSource

    @property
    def is_printable(self):
        return self.material.upper() == "PETG"


class BOMTable(BaseModel):
    items: List[BOMItem]

    @classmethod
    def parse_onshape(cls, onshape_data):
        return cls(
            items=[
                BOMItem(
                    name=item["name"], 
                    description=item["description"], 
                    material=item["material"]["id"] if isinstance(item["material"], dict) else item["material"], 
                    quantity=item["quantity"], 
                    source=ItemSource(
                        configuration=item["itemSource"]["fullConfiguration"],
                        did=item["itemSource"]["documentId"],
                        eid=item["itemSource"]["elementId"],
                        wvm_type=item["itemSource"]["wvmType"],
                        wvm_id=item["itemSource"]["wvmId"],
                        part_id=item["itemSource"]["partId"],
                    )
                ) for item in onshape_data["bomTable"]["items"]
            ]
        )
