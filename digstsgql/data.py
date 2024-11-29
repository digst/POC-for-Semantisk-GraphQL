import csv
import textwrap
from collections.abc import Iterable

from digstsgql import db


def _parse(data: str) -> list[dict[str, str]]:
    """Parse "csv" (xlsx copy-pasted from libreoffice)."""
    lines = textwrap.dedent(data).splitlines()
    reader = csv.DictReader(lines, delimiter="\t")
    return [row for row in reader]


def myndighed() -> Iterable[db.Myndighed]:
    """Myndighed.xlsx."""
    data = """\
    id	myndighedskode
    4493ba96-87d5-4d81-9b94-7123d6813091	550
    """
    for r in _parse(data):
        yield db.Myndighed(
            id=r["id"],
            myndighedskode=r["myndighedskode"],
        )


def organisation() -> Iterable[db.Organisation]:
    """Organisation.xlsx."""
    # NOTE:
    # - mynidighed_id renamed to myndighed_id.
    # - 61fc2005-5e7c-44cd-6720-0f8f8864e1b4 was originally 61fc2005-5e7c-44cd-672-0f8f8864e1b4 (an invalid uuid).
    data = """\
    id	brugervendtnoegle	organisationsnavn	topenhed_id	virksomhed_id	myndighed_id
    bcd7008d-3287-48be-a456-d9667e7ce777	Korsbæk Kommune	Korsbæk Kommune	b9e45b18-b6ba-4434-bce4-844214aaaae8
    9eb2e5cf-b6ea-457a-a4c0-a639c1aa3efa	FOTM Grønland 1 IVS 	Grønland 1 IVS 	f2fb84a1-43f2-408c-adf0-5124e552749e	420f1c67-cbf9-408b-961a-427db149d7ab
    46d5e14c-5ee9-4ea7-bad2-d98dd0f86163	FOTM Sørensen ApS 	Sørensen ApS 	c3c389c6-85fa-4c4d-aec4-ab5754149149	c41e9c1a-48a9-4caa-81b4-e8fe9af2ef95
    28609960-b8db-4bfe-8291-b1241214e23d	FOTM Christiansen ApS 	Christiansen ApS 	d42883a2-9e6e-4081-bace-c6e8207da6d7	b9d32f2d-0af2-4685-9187-42ad62141583
    aa2d6d8b-ee55-4f5a-99a0-10577388c1b7	FOTM Davidsen A/S	Davidsen A/S	701dad17-8145-4db8-9d9a-9750ad4beeeb	61fc2005-5e7c-44cd-6720-0f8f8864e1b4
    cfd96638-b91f-4ff1-861d-5d8859249d4e	FOTM Kosteland I/S	Kosteland I/S	1cd7ed13-0d98-4bb2-a907-d5ba5e723308	8c18da7f-0b19-4d0a-93a6-8df37c781a5c
    3b7263e9-a346-46e0-b3c0-f5f369de2a90	FOTM Søndergaard	Søndergaard	da387046-7803-446b-9c2e-625957ef4627	98caf558-2095-4ecd-9474-a905e797cd67
    b56f4d4a-1ed6-47b7-9466-03b7c641fa34	FOTM skytteforening	FOTM skytteforening	abb5d1fe-c7ff-447e-95db-ff05dbc30748	3d5a1d7b-9ed3-4d83-9c8b-b1a60c68d288
    fc8b67c3-cf90-4b74-a59e-9fe31486a4e8	FOTM kommune	FOTM kommune	ca2dead0-6cfc-499a-a6f6-0f3952cc6021	5c846f62-ac0e-4e0b-97a9-4c29c4b0ecd0
    74b662e7-4e86-4623-a053-989ab7b1ca95	FOTM region	FOTM region	c1939b9b-14aa-40b5-891c-818f8f895ca3	0c4c2f91-d3dc-4ee0-95a9-980282aad803
    e4373cde-1d5f-443a-b2df-94f7362ef40a	Klimadatastyrelsen	Klimadatastyrelsen	db346f3d-d31c-4d6d-8593-8b2df75fd525	b5e6f1c3-cc29-4661-85d1-6ed27abff173
    aa601fe6-52f6-44cf-8e80-6a90fcc4d2bb	Tønder Kommune	Tønder Kommune	ecd575e1-f62e-411f-951d-7f6de2634b30	4493ba96-87d5-4d81-9b94-7123d6813091	4493ba96-87d5-4d81-9b94-7123d6813091
    """
    for r in _parse(data):
        yield db.Organisation(
            id=r["id"],
            brugervendtnoegle=r["brugervendtnoegle"],
            organisationsnavn=r["organisationsnavn"],
            # topenhed_id=r["topenhed_id"],
            virksomhed_id=r["virksomhed_id"],
            myndighed_id=r["myndighed_id"],
        )


def organisationenhed() -> Iterable[db.Organisationenhed]:
    """Organisationenhed.xlsx."""
    data = """\
    id	brugervendtnoegle	enhedsnavn	organisation_id	overordnetenhed_id
    b9e45b18-b6ba-4434-bce4-844214aaaae8	Korsbæk Kommune	Korsbæk Kommune	bcd7008d-3287-48be-a456-d9667e7ce777
    f2fb84a1-43f2-408c-adf0-5124e552749e	FOTM Grønland 1 IVS	Grønland 1 IVS	9eb2e5cf-b6ea-457a-a4c0-a639c1aa3efa
    c3c389c6-85fa-4c4d-aec4-ab5754149149	FOTM Sørensen ApS	Sørensen ApS	46d5e14c-5ee9-4ea7-bad2-d98dd0f86163
    d42883a2-9e6e-4081-bace-c6e8207da6d7	FOTM Christiansen ApS	Christiansen ApS	28609960-b8db-4bfe-8291-b1241214e23d
    701dad17-8145-4db8-9d9a-9750ad4beeeb	FOTM Davidsen A/S	Davidsen A/S	aa2d6d8b-ee55-4f5a-99a0-10577388c1b7
    1cd7ed13-0d98-4bb2-a907-d5ba5e723308	FOTM Kosteland I/S	Kosteland I/S	cfd96638-b91f-4ff1-861d-5d8859249d4e
    da387046-7803-446b-9c2e-625957ef4627	FOTM Søndergaard	Søndergaard	3b7263e9-a346-46e0-b3c0-f5f369de2a90
    abb5d1fe-c7ff-447e-95db-ff05dbc30748	FOTM skytteforening	FOTM skytteforening	b56f4d4a-1ed6-47b7-9466-03b7c641fa34
    ca2dead0-6cfc-499a-a6f6-0f3952cc6021	FOTM kommune	FOTM kommune	fc8b67c3-cf90-4b74-a59e-9fe31486a4e8
    c1939b9b-14aa-40b5-891c-818f8f895ca3	FOTM region	FOTM region	74b662e7-4e86-4623-a053-989ab7b1ca95
    db346f3d-d31c-4d6d-8593-8b2df75fd525	Klimadatastyrelsen	Klimadatastyrelsen	e4373cde-1d5f-443a-b2df-94f7362ef40a
    ecd575e1-f62e-411f-951d-7f6de2634b30	Tønder Kommune	Tønder Kommune	aa601fe6-52f6-44cf-8e80-6a90fcc4d2bb
    f5eb15f4-4c6c-4362-aebb-74359f650423	KDS_Direktion	Direktion	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    c856a563-6699-45a3-8f39-583b73685057	KDS_Direktionsbetjening, Kommunikation og HR	Direktionsbetjening, Kommunikation og HR	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    854fdafd-2562-4ad1-bc58-a9f71eb882c2	KDS_Økonomi og Koncernindkøb	Økonomi og Koncernindkøb	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    93a94c0d-32e0-4198-987b-81b2afb50a9d	KDS_Fællesoffentlig datadistribution	Fællesoffentlig datadistribution	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    35929cc3-553e-47b0-8c98-7ab5013e3a11	KDS_Geografiske referencer	Geografiske referencer	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    9396b481-3af6-4ef5-bbd2-a60f57ba03b8	KDS_Kortlægning	Kortlægning	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    468e63ef-0bd8-4c56-a299-4c5ec9752253	KDS_Forvaltningsdata	Forvaltningsdata	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    254d8a01-77a8-4b99-a4f9-85e70288698d	KDS_Geodata	Geodata	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    bf9f04ef-9bf8-43cd-b2a2-a1637687efec	KDS_Center for Jordobservationer og Datasammenstilling	Center for Jordobservationer og Datasammenstilling	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    bc0e243d-30a1-459c-8410-66f73a31db54	KDS_Center for Forretningsudvikling og Grøn Omstilling	Center for Forretningsudvikling og Grøn Omstilling	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    cc3f23dd-bb0d-4688-a1bf-02cc5fc17631	KDS_Center for IT	Center for IT	e4373cde-1d5f-443a-b2df-94f7362ef40a	db346f3d-d31c-4d6d-8593-8b2df75fd525
    9e491092-be32-4a74-a8b6-a3868386958d	Social og Sundhedsforvaltningen	Social og Sundhedsforvaltningen	bcd7008d-3287-48be-a456-d9667e7ce777	b9e45b18-b6ba-4434-bce4-844214aaaae8
    6bbd954b-ef5f-426e-b387-aa92a0acc8ac	Beskæftigelsesområdet	Beskæftigelsesområdet	bcd7008d-3287-48be-a456-d9667e7ce777	9e491092-be32-4a74-a8b6-a3868386958d
    e0fb33b7-ee59-43f4-af5b-faf67de2c549	Sundhed, Udvikling, Service og Økonomi	Sundhed, Udvikling, Service og Økonomi	bcd7008d-3287-48be-a456-d9667e7ce777	9e491092-be32-4a74-a8b6-a3868386958d
    e5044026-9fc9-485a-a3bb-428a004c0483	Ungeområdet	Ungeområdet	bcd7008d-3287-48be-a456-d9667e7ce777	6bbd954b-ef5f-426e-b387-aa92a0acc8ac
    e265f56e-031f-46b5-a403-6ded21e8d3e2	Jobcenter	Jobcenter	bcd7008d-3287-48be-a456-d9667e7ce777	6bbd954b-ef5f-426e-b387-aa92a0acc8ac
    bd145a83-5386-40c8-b0e6-4fa5f6298c95	Ydelse og Rådighed	Ydelse og Rådighed	bcd7008d-3287-48be-a456-d9667e7ce777	e265f56e-031f-46b5-a403-6ded21e8d3e2
    b1f926f5-47fd-4b3e-a4fc-01f21bc5d7e1	Job og Ressourcer	Job og Ressourcer	bcd7008d-3287-48be-a456-d9667e7ce777	e265f56e-031f-46b5-a403-6ded21e8d3e2
    03d0923b-fa25-4991-84ed-b060379c7a31	Job og Kompetencer	Job og Kompetencer	bcd7008d-3287-48be-a456-d9667e7ce777	e265f56e-031f-46b5-a403-6ded21e8d3e2
    2fd959da-55a2-46c5-9137-05f171c0ed88	Borgerservice	Borgerservice	bcd7008d-3287-48be-a456-d9667e7ce777	e0fb33b7-ee59-43f4-af5b-faf67de2c549
    51477a5b-8cf4-4aaa-a2a9-b25fc7d435fb	Økonomi og Styring	Økonomi og Styring	bcd7008d-3287-48be-a456-d9667e7ce777	e0fb33b7-ee59-43f4-af5b-faf67de2c549
    fb07f74b-bee1-4995-88d7-a38f29fbada2	Folkeregister	Folkeregister	bcd7008d-3287-48be-a456-d9667e7ce777	2fd959da-55a2-46c5-9137-05f171c0ed88
    30d1e7a1-ca9f-494d-afc6-c558ff103149	Pension	Pension	bcd7008d-3287-48be-a456-d9667e7ce777	2fd959da-55a2-46c5-9137-05f171c0ed88
    77214ba0-b7c8-40e9-91d3-8ac8eb318e02	Kontrolgruppen	Kontrolgruppen	bcd7008d-3287-48be-a456-d9667e7ce777	2fd959da-55a2-46c5-9137-05f171c0ed88
    91d885e9-e109-4c11-9f81-aa1641b67e49	Info-Omstilling	Info-Omstilling	bcd7008d-3287-48be-a456-d9667e7ce777	2fd959da-55a2-46c5-9137-05f171c0ed88
    20aa5884-b888-4b25-8f32-9f914ea3c59a	Børne og Kulturforvaltningen	Børne og Kulturforvaltningen	bcd7008d-3287-48be-a456-d9667e7ce777	b9e45b18-b6ba-4434-bce4-844214aaaae8
    e9ed0144-a271-4795-a338-3e42a422eaa4	Økonomi og Analyse	Økonomi og Analyse	bcd7008d-3287-48be-a456-d9667e7ce777	20aa5884-b888-4b25-8f32-9f914ea3c59a
    cc260f6a-87b5-4119-b68f-3e8014f4154f	Familie og rådgivning	Familie og rådgivning	bcd7008d-3287-48be-a456-d9667e7ce777	20aa5884-b888-4b25-8f32-9f914ea3c59a
    19681aea-d35d-4532-a342-b274554f2b28	Dagtilbud og Sundhed	Dagtilbud og Sundhed	bcd7008d-3287-48be-a456-d9667e7ce777	20aa5884-b888-4b25-8f32-9f914ea3c59a
    f8ab8cf9-8789-41d5-880e-9477b39d310c	Kultur, Fritid og Unge	Kultur, Fritid og Unge	bcd7008d-3287-48be-a456-d9667e7ce777	20aa5884-b888-4b25-8f32-9f914ea3c59a
    05411b7e-cadd-4e7b-ad25-f84a562e6b94	Pædagogisk Psykologisk Rådgivning	Pædagogisk Psykologisk Rådgivning	bcd7008d-3287-48be-a456-d9667e7ce777	cc260f6a-87b5-4119-b68f-3e8014f4154f
    e625d9d4-e6cb-4bf3-8d16-86531273f5e5	Familieafdelingen	Familieafdelingen	bcd7008d-3287-48be-a456-d9667e7ce777	cc260f6a-87b5-4119-b68f-3e8014f4154f
    79d033ab-941f-4f86-bbd8-6878f519708f	PPR Team 1	PPR Team 1	bcd7008d-3287-48be-a456-d9667e7ce777	05411b7e-cadd-4e7b-ad25-f84a562e6b94
    a975dede-d47a-40c9-99d6-b3e85c7979d7	PPR Team 2	PPR Team 2	bcd7008d-3287-48be-a456-d9667e7ce777	05411b7e-cadd-4e7b-ad25-f84a562e6b94
    70a1ee92-69ce-48e2-9074-2cc284aae311	Social og Handicapafdelingen	Social og Handicapafdelingen	bcd7008d-3287-48be-a456-d9667e7ce777	9e491092-be32-4a74-a8b6-a3868386958d
    178e5c78-d568-43dd-a580-54296929bb1d	Den Boligsociale Enhed	Den Boligsociale Enhed	bcd7008d-3287-48be-a456-d9667e7ce777	70a1ee92-69ce-48e2-9074-2cc284aae311
    e3036f8b-11d1-49d7-908c-101013cde24f	Det Psykosociale område	Det Psykosociale område	bcd7008d-3287-48be-a456-d9667e7ce777	70a1ee92-69ce-48e2-9074-2cc284aae311
    86390518-8e34-4466-a115-f12bea39cf04	Handicaprådgivningen	Handicaprådgivningen	bcd7008d-3287-48be-a456-d9667e7ce777	70a1ee92-69ce-48e2-9074-2cc284aae311
    23cbb3b0-179a-49d7-98f5-0d93280972a0	Korsbæk Handicaptilbud	Korsbæk Handicaptilbud	bcd7008d-3287-48be-a456-d9667e7ce777	70a1ee92-69ce-48e2-9074-2cc284aae311
    """
    for r in _parse(data):
        yield db.Organisationenhed(
            id=r["id"],
            brugervendtnoegle=r["brugervendtnoegle"],
            enhedsnavn=r["enhedsnavn"],
            organisation_id=r["organisation_id"],
            overordnetenhed_id=r["overordnetenhed_id"],
        )


def virksomhed() -> Iterable[db.Virksomhed]:
    """Virksomhed.xlsx."""
    # NOTE:
    # - 61fc2005-5e7c-44cd-6720-0f8f8864e1b4 was originally 61fc2005-5e7c-44cd-672-0f8f8864e1b4 (an invalid uuid).
    data = """\
    id	cvr_nummer
    420f1c67-cbf9-408b-961a-427db149d7ab	45152278
    c41e9c1a-48a9-4caa-81b4-e8fe9af2ef95	45152286
    b9d32f2d-0af2-4685-9187-42ad62141583	45152294
    61fc2005-5e7c-44cd-6720-0f8f8864e1b4	45152308
    8c18da7f-0b19-4d0a-93a6-8df37c781a5c	45152324
    98caf558-2095-4ecd-9474-a905e797cd67	45152332
    3d5a1d7b-9ed3-4d83-9c8b-b1a60c68d288	45152340
    5c846f62-ac0e-4e0b-97a9-4c29c4b0ecd0	45152367
    0c4c2f91-d3dc-4ee0-95a9-980282aad803	45152375
    b5e6f1c3-cc29-4661-85d1-6ed27abff173	37284114
    4493ba96-87d5-4d81-9b94-7123d6813091	29189781
    """
    for r in _parse(data):
        yield db.Virksomhed(
            id=r["id"],
            cvr_nummer=r["cvr_nummer"],
        )
