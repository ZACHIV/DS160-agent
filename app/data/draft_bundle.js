window.DS160_DRAFT_BUNDLE = {
  "case_id": "CN-B1B2-001",
  "summary": {
    "status_counts": {
      "ready": 26,
      "needs_review": 2,
      "blocked": 1
    },
    "page_count": 12,
    "hard_stops": [
      "stop_on_captcha",
      "stop_on_applicant_signature",
      "stop_on_photo_failure",
      "stop_for_operator_review_queue",
      "stop_for_missing_required_data"
    ]
  },
  "top_steps": [
    {
      "id": "complete",
      "label": "COMPLETE"
    },
    {
      "id": "photo",
      "label": "PHOTO"
    },
    {
      "id": "review",
      "label": "REVIEW"
    },
    {
      "id": "sign",
      "label": "SIGN"
    }
  ],
  "navigation": [
    {
      "section_id": "getting_started",
      "label": "Getting Started",
      "pages": [
        {
          "page_id": "getting_started",
          "label": "Getting Started",
          "status": "reference"
        }
      ]
    },
    {
      "section_id": "personal",
      "label": "Personal",
      "pages": [
        {
          "page_id": "personal_page_1",
          "label": "Personal 1",
          "status": "implemented"
        },
        {
          "page_id": "personal_page_2",
          "label": "Personal 2",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "travel",
      "label": "Travel",
      "pages": [
        {
          "page_id": "travel_page",
          "label": "Travel",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "travel_companions",
      "label": "Travel Companions",
      "pages": [
        {
          "page_id": "travel_companions_page",
          "label": "Travel Companions",
          "status": "planned"
        }
      ]
    },
    {
      "section_id": "previous_us_travel",
      "label": "Previous U.S. Travel",
      "pages": [
        {
          "page_id": "previous_us_travel_page",
          "label": "Previous U.S. Travel",
          "status": "planned"
        }
      ]
    },
    {
      "section_id": "address_phone",
      "label": "Address and Phone",
      "pages": [
        {
          "page_id": "address_phone_page",
          "label": "Address and Phone",
          "status": "planned"
        }
      ]
    },
    {
      "section_id": "passport",
      "label": "Passport",
      "pages": [
        {
          "page_id": "passport_page",
          "label": "Passport",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "us_contact",
      "label": "U.S. Contact",
      "pages": [
        {
          "page_id": "us_contact_page",
          "label": "U.S. Contact",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "family",
      "label": "Family",
      "pages": [
        {
          "page_id": "family_page",
          "label": "Family",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "work_education_training",
      "label": "Work / Education / Training",
      "pages": [
        {
          "page_id": "employment_page",
          "label": "Work / Education / Training",
          "status": "implemented"
        }
      ]
    },
    {
      "section_id": "security_background",
      "label": "Security and Background",
      "pages": [
        {
          "page_id": "security_page",
          "label": "Security and Background",
          "status": "implemented"
        }
      ]
    }
  ],
  "pages": [
    {
      "page_id": "getting_started",
      "label": "Getting Started",
      "save_checkpoint": null,
      "fill": [],
      "review": [],
      "blocked": [],
      "autofill_count": 0,
      "review_count": 0,
      "blocked_count": 0,
      "status": "reference",
      "notes": [
        "入口页，不属于正式表单字段填写。"
      ]
    },
    {
      "page_id": "personal_page_1",
      "label": "Personal 1",
      "save_checkpoint": "save_after_identity_page",
      "fill": [
        {
          "action_type": "fill",
          "field_id": "identity.surname",
          "locator_key": "identity_surname",
          "proposed_value": "ZHANG",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.given_names",
          "locator_key": "identity_given_names",
          "proposed_value": "WEI",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.native_full_name",
          "locator_key": "identity_native_full_name",
          "proposed_value": "张伟",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": "Native alphabet field is supplied from PRC passport data when available."
        },
        {
          "action_type": "fill",
          "field_id": "identity.sex",
          "locator_key": "identity_sex",
          "proposed_value": "MALE",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.marital_status",
          "locator_key": "identity_marital_status",
          "proposed_value": "MARRIED",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.date_of_birth",
          "locator_key": "identity_date_of_birth",
          "proposed_value": "1990-08-15",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.birth_city",
          "locator_key": "identity_birth_city",
          "proposed_value": "SHANGHAI",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.birth_country",
          "locator_key": "identity_birth_country",
          "proposed_value": "CHINA",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "identity.nationality",
          "locator_key": "identity_nationality",
          "proposed_value": "CHINA",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "passport.number",
          "locator_key": "passport_number",
          "proposed_value": "E12345678",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "passport.issue_date",
          "locator_key": "passport_issue_date",
          "proposed_value": "2023-05-12",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "passport.expiration_date",
          "locator_key": "passport_expiration_date",
          "proposed_value": "2033-05-11",
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": null
        }
      ],
      "review": [
        {
          "action_type": "review",
          "field_id": "passport.book_number",
          "locator_key": "passport_book_number",
          "proposed_value": null,
          "evidence_refs": [
            "passport_scan"
          ],
          "notes": "Chinese applicants often do not have a passport book number; confirm whether DS-160 should be marked as not applicable."
        }
      ],
      "blocked": [],
      "autofill_count": 12,
      "review_count": 1,
      "blocked_count": 0,
      "status": "implemented",
      "notes": []
    },
    {
      "page_id": "personal_page_2",
      "label": "Personal 2",
      "save_checkpoint": null,
      "fill": [],
      "review": [],
      "blocked": [],
      "autofill_count": 0,
      "review_count": 0,
      "blocked_count": 0,
      "status": "implemented",
      "notes": []
    },
    {
      "page_id": "travel_page",
      "label": "Travel",
      "save_checkpoint": "save_after_travel_page",
      "fill": [
        {
          "action_type": "fill",
          "field_id": "travel.intended_arrival_date",
          "locator_key": "travel_intended_arrival_date",
          "proposed_value": "2026-09-10",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.intended_length_of_stay",
          "locator_key": "travel_intended_length_of_stay",
          "proposed_value": "12 DAYS",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.payer_name",
          "locator_key": "travel_payer_name",
          "proposed_value": "Shanghai Example Trading Co., Ltd.",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.us_contact_name",
          "locator_key": "travel_us_contact_name",
          "proposed_value": "Michael Chen",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.us_contact_address_line1",
          "locator_key": "travel_us_contact_address_line1",
          "proposed_value": "500 Market Street",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.us_contact_city",
          "locator_key": "travel_us_contact_city",
          "proposed_value": "San Francisco",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.us_contact_state",
          "locator_key": "travel_us_contact_state",
          "proposed_value": "California",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "travel.us_contact_postal_code",
          "locator_key": "travel_us_contact_postal_code",
          "proposed_value": "94105",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": null
        }
      ],
      "review": [
        {
          "action_type": "review",
          "field_id": "travel.purpose_of_trip",
          "locator_key": "travel_purpose_of_trip",
          "proposed_value": "B1/B2",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": "Mixed business/tourism cases should be confirmed by an operator before final submission."
        }
      ],
      "blocked": [
        {
          "action_type": "block",
          "field_id": "travel.us_contact_phone",
          "locator_key": "travel_us_contact_phone",
          "proposed_value": null,
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ],
          "notes": "U.S. contact phone is missing."
        }
      ],
      "autofill_count": 8,
      "review_count": 1,
      "blocked_count": 1,
      "status": "implemented",
      "notes": []
    },
    {
      "page_id": "travel_companions_page",
      "label": "Travel Companions",
      "save_checkpoint": null,
      "fill": [],
      "review": [],
      "blocked": [],
      "autofill_count": 0,
      "review_count": 0,
      "blocked_count": 0,
      "status": "planned",
      "notes": [
        "流程按钮已补齐，本地草稿尚未建模。"
      ]
    },
    {
      "page_id": "previous_us_travel_page",
      "label": "Previous U.S. Travel",
      "save_checkpoint": null,
      "fill": [],
      "review": [],
      "blocked": [],
      "autofill_count": 0,
      "review_count": 0,
      "blocked_count": 0,
      "status": "planned",
      "notes": [
        "流程按钮已补齐，本地草稿尚未建模。"
      ]
    },
    {
      "page_id": "address_phone_page",
      "label": "Address and Phone",
      "save_checkpoint": null,
      "fill": [],
      "review": [],
      "blocked": [],
      "autofill_count": 0,
      "review_count": 0,
      "blocked_count": 0,
      "status": "planned",
      "notes": [
        "流程按钮已补齐，本地草稿尚未建模。"
      ]
    },
    {
      "page_id": "passport_page",
      "label": "Passport",
      "save_checkpoint": null,
      "fill": [
        {
          "field_id": "passport.number",
          "proposed_value": "E12345678",
          "evidence_refs": [
            "passport_scan"
          ]
        },
        {
          "field_id": "passport.issue_date",
          "proposed_value": "2023-05-12",
          "evidence_refs": [
            "passport_scan"
          ]
        },
        {
          "field_id": "passport.expiration_date",
          "proposed_value": "2033-05-11",
          "evidence_refs": [
            "passport_scan"
          ]
        },
        {
          "field_id": "passport.issuance_country",
          "proposed_value": "CHINA",
          "evidence_refs": [
            "passport_scan"
          ]
        }
      ],
      "review": [
        {
          "field_id": "passport.book_number",
          "notes": "Chinese applicants often do not have a passport book number; confirm whether DS-160 should be marked as not applicable."
        }
      ],
      "blocked": [],
      "autofill_count": 4,
      "review_count": 1,
      "blocked_count": 0,
      "status": "implemented",
      "notes": [
        "护照页已建模，护照本编号默认进入人工确认。"
      ]
    },
    {
      "page_id": "us_contact_page",
      "label": "U.S. Contact",
      "save_checkpoint": null,
      "fill": [
        {
          "field_id": "travel.us_contact_name",
          "proposed_value": "Michael Chen",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        },
        {
          "field_id": "travel.us_contact_organization",
          "proposed_value": "Example US Imports",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        },
        {
          "field_id": "travel.us_contact_address_line1",
          "proposed_value": "500 Market Street",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        },
        {
          "field_id": "travel.us_contact_city",
          "proposed_value": "San Francisco",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        },
        {
          "field_id": "travel.us_contact_state",
          "proposed_value": "California",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        },
        {
          "field_id": "travel.us_contact_postal_code",
          "proposed_value": "94105",
          "evidence_refs": [
            "itinerary_email",
            "invitation_letter"
          ]
        }
      ],
      "review": [],
      "blocked": [
        {
          "field_id": "travel.us_contact_phone",
          "notes": "U.S. contact phone is missing."
        }
      ],
      "autofill_count": 6,
      "review_count": 0,
      "blocked_count": 1,
      "status": "implemented",
      "notes": [
        "美国联系人页已建模，当前仍缺联系人电话。"
      ]
    },
    {
      "page_id": "family_page",
      "label": "Family",
      "save_checkpoint": null,
      "fill": [
        {
          "action_type": "fill",
          "field_id": "family.father_full_name",
          "locator_key": "family_father_full_name",
          "proposed_value": "ZHANG JIANGUO",
          "evidence_refs": [
            "family_intake_form"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "family.mother_full_name",
          "locator_key": "family_mother_full_name",
          "proposed_value": "LI HUA",
          "evidence_refs": [
            "family_intake_form"
          ],
          "notes": null
        }
      ],
      "review": [],
      "blocked": [],
      "autofill_count": 2,
      "review_count": 0,
      "blocked_count": 0,
      "status": "implemented",
      "notes": []
    },
    {
      "page_id": "employment_page",
      "label": "Work / Education / Training",
      "save_checkpoint": "save_after_employment_page",
      "fill": [
        {
          "action_type": "fill",
          "field_id": "employment.primary_occupation",
          "locator_key": "employment_primary_occupation",
          "proposed_value": "BUSINESSPERSON",
          "evidence_refs": [
            "employment_letter"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "employment.current_employer_name",
          "locator_key": "employment_current_employer_name",
          "proposed_value": "Shanghai Example Trading Co., Ltd.",
          "evidence_refs": [
            "employment_letter"
          ],
          "notes": null
        }
      ],
      "review": [],
      "blocked": [],
      "autofill_count": 2,
      "review_count": 0,
      "blocked_count": 0,
      "status": "implemented",
      "notes": []
    },
    {
      "page_id": "security_page",
      "label": "Security and Background",
      "save_checkpoint": "save_before_security_page",
      "fill": [
        {
          "action_type": "fill",
          "field_id": "security.communicable_disease",
          "locator_key": "security_communicable_disease",
          "proposed_value": false,
          "evidence_refs": [
            "security_review_form"
          ],
          "notes": null
        },
        {
          "action_type": "fill",
          "field_id": "security.arrest_history",
          "locator_key": "security_arrest_history",
          "proposed_value": false,
          "evidence_refs": [
            "security_review_form"
          ],
          "notes": null
        }
      ],
      "review": [],
      "blocked": [],
      "autofill_count": 2,
      "review_count": 0,
      "blocked_count": 0,
      "status": "implemented",
      "notes": []
    }
  ]
};
