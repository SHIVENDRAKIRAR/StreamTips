from pydantic import BaseModel, ConfigDict


class CreatorPublicProfile(BaseModel):
    """
    What a viewer sees on /@creator. Deliberately minimal — no email,
    no overlay_token, no internal id exposure beyond what's needed to
    render the tip page.
    """
    model_config = ConfigDict(from_attributes=True)

    username: str
    display_name: str
