"""Curated crop guidance summaries from named agricultural institutions.

These English-language notes are intentionally conservative. The linked
institutional source is authoritative; local recommendations vary by state,
season, soil, variety, irrigation and crop stage.
"""

TNAU = "Tamil Nadu Agricultural University (TNAU)"

DOCUMENTS = [
    {
        "title": "Rice cultivation, field preparation and harvest",
        "content": (
            "TNAU's rice crop-production guide covers seed and nursery management, main-field preparation and transplanting, "
            "nutrient management, irrigation, weed management and harvest. Prepare and level the field to suit the selected "
            "rice establishment method and ensure drainage where needed. Use a locally recommended variety and season. Base "
            "nutrient decisions on a soil test and crop stage rather than applying a blanket dose from a general conversation. "
            "The guide identifies panicle initiation, booting, heading and flowering as important water-sensitive stages; "
            "avoid water stress at these stages and prevent excessive standing water. Follow local crop maturity indicators and drain water before harvest when advised for the production system."
        ),
        "crop": "rice paddy వరి നെல்",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest సాగు నేల తయారీ నీరు నీటిపారుదల ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/ta/pdf/2013/CPG%202012.pdf",
    },
    {
        "title": "Rice irrigation and water-sensitive growth stages",
        "content": (
            "TNAU identifies panicle initiation, booting, heading and flowering as critical stages for rice water management. "
            "Puddling and leveling can reduce water requirement in transplanted lowland systems. Maintain soil moisture with "
            "an irrigation schedule suited to soil, weather, variety and establishment method; excessive continuous flooding "
            "can also harm crop performance. This is general source-backed guidance, not a field-specific schedule."
        ),
        "crop": "rice paddy వరి",
        "topic": "irrigation water నీరు నీటిపారుదల",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://www.agritech.tnau.ac.in/agriculture/agri_irrigationmgt_cereals_rice.html",
    },
    {
        "title": "Rice shallow water guidance for flowering to milk stage",
        "content": (
            "ICAR-CIWA describes maintaining a shallow 3–5 cm water level during the period from flowering to milk stage. "
            "Use this as a reference only: irrigation decisions depend on rainfall, soil, crop establishment and local water "
            "management recommendations. This note is not a live field-specific irrigation schedule."
        ),
        "crop": "rice paddy వరి",
        "topic": "irrigation water నీరు నీటిపారుదల",
        "language": "en",
        "source_name": "ICAR-CIWA",
        "source_url": "https://www.ciwa.icar.gov.in/gks/crop-production",
    },
    {
        "title": "Cotton soil preparation, crop care and picking",
        "content": (
            "TNAU's cotton guide recommends preparing a suitable seedbed and using ridges and furrows or beds according to "
            "the field and irrigation method. It advises soil-test-based NPK management and regulating irrigation for soil "
            "type, weather and rainfall, with attention to square formation and boll development/maturity. The guide describes "
            "harvesting opened kapas at frequent intervals. These instructions are state-guide context; variety, rainfed or "
            "irrigated system and local crop calendar change the correct practice."
        ),
        "crop": "cotton పత్తి పత్తి పంట",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest picking సాగు నేల నీరు ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/agriculture/CropProduction/Fibre%20crops/fibrecrops_cotton.html",
    },
    {
        "title": "Cotton pest and disease monitoring",
        "content": (
            "TNAU's cotton integrated pest management material lists pests such as bollworms, whitefly, jassid and thrips, "
            "and diseases including cotton leaf curl virus and wilt/root problems. Regularly inspect plants and record the "
            "crop stage, affected area and spread before taking action. Field sanitation and early removal of volunteer host "
            "weeds are described as preventive measures. Similar leaf symptoms can have different causes; seek a local crop "
            "protection officer's confirmation before treatment. This summary does not recommend pesticide products or doses."
        ),
        "crop": "cotton పత్తి",
        "topic": "pest insect disease prevention scouting bollworm whitefly jassid thrips virus తెగులు పురుగు వ్యాధి నివారణ",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_pdf/cotton.pdf",
    },
    {
        "title": "Chilli establishment, irrigation and nutrient care",
        "content": (
            "TNAU's chilli cultivation guide describes preparing a well-tilled field, forming ridges/furrows or beds, and "
            "transplanting healthy seedlings. Irrigation must follow soil moisture, rainfall and field drainage; waterlogging "
            "should be avoided. Flowering and fruit development are important water-demand stages. Use soil-test results and "
            "local horticulture recommendations for nutrient planning. Harvest mature fruits at the stage and frequency "
            "appropriate to the variety and whether green or dry chilli is intended. Exact timing and input needs vary by "
            "region and production system."
        ),
        "crop": "chilli chili pepper మిరప మిర్చి",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest సాగు నేల నీరు ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/horticulture/horti_vegetables_chilli_cultural.html",
    },
    {
        "title": "Chilli common diseases and preventive practices",
        "content": (
            "TNAU lists chilli problems including damping-off, anthracnose/die-back/fruit rot, leaf spots, powdery mildew, "
            "wilt, leaf curl and mosaic viruses. These symptoms can overlap and require crop-stage and field inspection for "
            "identification. The source describes preventive practices such as clean seed/seedlings, good drainage, crop "
            "rotation and removing diseased plants or infected residues. Avoid pesticide selection based only on a text "
            "description; consult a qualified local agriculture or horticulture officer for diagnosis and treatment."
        ),
        "crop": "chilli chili pepper మిరప మిర్చి",
        "topic": "pest insect disease prevention damping off anthracnose fruit rot leaf spot powdery mildew wilt leaf curl mosaic scouting తెగులు పురుగు వ్యాధి నివారణ",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg_chilli.html",
    },
    {
        "title": "Maize land preparation, moisture and harvest",
        "content": (
            "TNAU's maize guides describe preparing a fine seedbed and providing field channels/ridges or beds suited to the "
            "field. Maize is sensitive to both moisture stress and excess water; keep moisture adequate around flowering and "
            "avoid water stagnation. Follow locally recommended hybrid/variety and soil-test-based nutrient management; the "
            "specific recommendations differ between rainfed and irrigated systems and soil types. TNAU describes harvest "
            "when the cob sheath yellows and kernels become hard and dry."
        ),
        "crop": "maize corn మొక్కజొన్న",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest సాగు నేల నీరు ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/agriculture/millets_maize_irrigated_maize.html",
    },
    {
        "title": "Maize fall armyworm prevention and scouting",
        "content": (
            "ICAR's Kharif agro-advisories identify fall armyworm as a maize risk and describe preventive and monitoring "
            "measures. Inspect the whorl and leaves regularly for egg masses, young larvae and fresh damage; remove egg masses "
            "or larvae where feasible and use locally advised monitoring measures. A suspected outbreak should be assessed "
            "by crop stage and infestation level. Do not apply a pesticide solely from a text-based identification; contact "
            "the local agriculture officer for current, state-approved advice."
        ),
        "crop": "maize corn మొక్కజొన్న",
        "topic": "pest insect disease prevention scouting fall armyworm FAW పురుగు తెగులు వ్యాధి నివారణ",
        "language": "en",
        "source_name": "Indian Council of Agricultural Research (ICAR)",
        "source_url": "https://icar.gov.in/sites/default/files/2025-10/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf",
    },
    {
        "title": "Groundnut cultivation, soil test and harvest",
        "content": (
            "TNAU's groundnut crop-management guide describes preparing a fine seedbed, using beds suited to slope and soil, "
            "and basing fertilizer application on a soil test. It covers sowing, weed management and crop care. Groundnut "
            "flowering and pod development need attention to soil moisture, but the irrigation decision depends on rainfall, "
            "soil and crop stage. The guide describes checking representative pods at maturity; older leaves drying and "
            "yellowing and a dark inner shell are indicators to assess alongside variety duration. These are general field "
            "indicators, not a substitute for local crop advice."
        ),
        "crop": "groundnut peanut వేరుశనగ పల్లీ",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest pod సాగు నేల నీరు ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/CropProduction/Oilseeds/oilseeds_groundnut01.html",
    },
    {
        "title": "Groundnut leaf spot, rust and preventive field care",
        "content": (
            "TNAU identifies early/late leaf spot, rust, stem/root rot and bud necrosis among groundnut problems. Preventive "
            "field practices include regular scouting, crop rotation with non-host crops, removing volunteer groundnut plants "
            "and managing infected crop residues. Leaf spots, rust and nutrient stress can look similar to an untrained eye; "
            "record where symptoms begin and how quickly they spread, then request a qualified diagnosis before treatment. "
            "This note does not give a chemical recommendation."
        ),
        "crop": "groundnut peanut వేరుశనగ పల్లీ",
        "topic": "pest insect disease prevention scouting leaf spot rust stem rot root rot bud necrosis తెగులు పురుగు వ్యాధి నివారణ",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/org_farm/orgfarm_agridiseases.html",
    },
    {
        "title": "Tomato field preparation, irrigation and crop care",
        "content": (
            "TNAU's tomato cultivation materials cover season and field preparation, nursery, cultural practices, irrigation, "
            "nutrient management, pests, diseases and post-harvest handling. Prepare a well-drained field and avoid standing "
            "water around nursery beds and plants. Adjust irrigation to soil moisture, rainfall and crop stage. Base nutrient "
            "decisions on soil tests and local horticulture guidance rather than a universal dose. Harvest at the maturity "
            "stage suitable for the market and transport distance; local variety and season affect timing."
        ),
        "crop": "tomato టమాటా టమాట",
        "topic": "cultivation soil preparation irrigation water fertilizer nutrient harvest nursery సాగు నేల నీరు ఎరువు కోత",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/horticulture/horti_vegetables_tomato_cultural%20practices.html",
    },
    {
        "title": "Tomato fruit borer and whitefly scouting",
        "content": (
            "TNAU tomato IPM materials describe fruit borers such as Helicoverpa and Spodoptera, whitefly, leaf miner and "
            "root-knot nematode among potential pests, and discuss field scouting, sanitation and integrated practices. "
            "Inspect leaves, flowers and fruit for fresh damage and record affected plants. Remove and safely dispose of "
            "damaged fruits where practical. Whitefly and leaf curl symptoms or fruit holes can have more than one cause; "
            "seek local expert identification before deciding on treatment. No pesticide dose is recommended here."
        ),
        "crop": "tomato టమాటా టమాట",
        "topic": "pest insect disease prevention scouting fruit borer whitefly leaf miner nematode తెగులు పురుగు వ్యాధి నివారణ",
        "language": "en",
        "source_name": TNAU,
        "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_pdf/tomato.pdf",
    },
    {
        "title": "General integrated pest management principles",
        "content": (
            "The Government of Meghalaya's agriculture department describes integrated pest management practices across "
            "crops: clean field preparation, removal of crop residues and weeds, suitable varieties, timely sowing, balanced "
            "nutrient and water management, regular monitoring of pests and natural enemies, conservation of beneficial "
            "organisms, and need-based action after monitoring. This is a general prevention framework, not crop-specific "
            "treatment advice. Follow the current state crop package and consult an agriculture officer for high-risk cases."
        ),
        "crop": "rice paddy వరి cotton పత్తి groundnut peanut వేరుశనగ tomato టమాటా chilli మిరప maize మొక్కజొన్న",
        "topic": "pest insect disease prevention scouting monitoring IPM integrated management crop rotation residue నివారణ తెగులు పురుగు వ్యాధి",
        "language": "en",
        "source_name": "Department of Agriculture, Government of Meghalaya",
        "source_url": "https://megagriculture.gov.in/PUBLIC/IPM_ipm.aspx",
    },
]
