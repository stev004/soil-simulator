# Phase 9.6 effect-only model card

Only paired intervention-minus-baseline biological effects are targets. Final stocks, deterministic cost/emissions and phosphorus headline claims are excluded. Location groups are isolated.

{
  "downstream_selection_executed": false,
  "excluded_headline_targets": [
    "final stock levels",
    "deterministic cost",
    "deterministic emissions",
    "phosphorus"
  ],
  "feature_separation": {
    "latent_excluded": [
      "AMF allocation",
      "AMF CUE",
      "AMF turnover",
      "necromass stabilisation",
      "hidden initial pools",
      "spin-up diagnostics"
    ],
    "observable": [
      "clay_percent",
      "silt_percent",
      "sand_percent",
      "bulk_density_g_cm3",
      "ph",
      "cation_exchange_capacity_cmolc_kg",
      "baseline_total_nitrogen_percent",
      "baseline_soc_t_c_ha",
      "mean_temperature_c",
      "annual_precipitation_mm",
      "annual_pet_mm"
    ]
  },
  "gates": {
    "all_effect_targets_beat_policy_mean": false,
    "all_effect_targets_have_acceptable_ood": false,
    "all_effect_targets_have_calibrated_uncertainty": true,
    "empirical_location_leakage_check": true,
    "independent_empirical_effect_validation": false
  },
  "stop_decision": "Stop: at least one predeclared prediction, OOD, uncertainty or independent-effect validation gate failed; no Phase 9.6 selector, oracle or regret benchmark was run.",
  "targets": {
    "delta_protected_soc_proxy_t_c_ha|120": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.18751007667190822,
        "policy_mean": {
          "bias": 0.051148902837371446,
          "mae": 0.09973500394457128,
          "r_squared": 0.9439584617474112,
          "rmse": 0.15485777029051845
        },
        "ridge": {
          "bias": -0.02307575665272142,
          "mae": 0.10997015197166997,
          "r_squared": 0.9534355778924658,
          "rmse": 0.141157866863291
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.875
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.18751007667190822,
        "policy_mean": {
          "bias": -0.0040287921535999225,
          "mae": 0.08105511802903273,
          "r_squared": 0.9665020476788461,
          "rmse": 0.13353189349601025
        },
        "ridge": {
          "bias": 0.006945061565109402,
          "mae": 0.08297669110672891,
          "r_squared": 0.9715016565953849,
          "rmse": 0.12316453883116124
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.875
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.11699374934406913
    },
    "delta_protected_soc_proxy_t_c_ha|60": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.10768952359815143,
        "policy_mean": {
          "bias": 0.025520874145929417,
          "mae": 0.05133819565589767,
          "r_squared": 0.9101380471966093,
          "rmse": 0.07833001317561837
        },
        "ridge": {
          "bias": -0.01405199183749369,
          "mae": 0.0574145758152226,
          "r_squared": 0.9246239593944772,
          "rmse": 0.07173926684249674
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.9166666666666666
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.10768952359815143,
        "policy_mean": {
          "bias": -0.002785089105658994,
          "mae": 0.04298377993180198,
          "r_squared": 0.9495646788995112,
          "rmse": 0.06765874817360544
        },
        "ridge": {
          "bias": -0.001767435140316086,
          "mae": 0.04351246456700067,
          "r_squared": 0.9589000807389613,
          "rmse": 0.06107690864117942
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.9134615384615384
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.06220769386910469
    },
    "delta_respiration_t_c_ha|120": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.8755470665661989,
        "policy_mean": {
          "bias": -0.04200108355346735,
          "mae": 0.3665040298958016,
          "r_squared": 0.9861457866648443,
          "rmse": 0.5224055663856662
        },
        "ridge": {
          "bias": -0.16398339083563357,
          "mae": 0.4140202439039533,
          "r_squared": 0.9854617840589707,
          "rmse": 0.5351461656596033
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.8333333333333334
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.8755470665661989,
        "policy_mean": {
          "bias": 0.006851628137416406,
          "mae": 0.3388910746269885,
          "r_squared": 0.9740009192432708,
          "rmse": 0.6525321464994223
        },
        "ridge": {
          "bias": 0.06878805726016449,
          "mae": 0.37896884139213927,
          "r_squared": 0.9760135666554681,
          "rmse": 0.6267664669891085
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.875
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.4776885375131893
    },
    "delta_respiration_t_c_ha|60": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.5184463168192819,
        "policy_mean": {
          "bias": 0.106303194889038,
          "mae": 0.25027960147265976,
          "r_squared": 0.9578240350739847,
          "rmse": 0.3453318922435422
        },
        "ridge": {
          "bias": -0.02535475304240667,
          "mae": 0.2600360380793802,
          "r_squared": 0.9635478735813695,
          "rmse": 0.32104477674653586
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.9166666666666666
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.5184463168192819,
        "policy_mean": {
          "bias": 0.01796801986684662,
          "mae": 0.1870602627970625,
          "r_squared": 0.9571065987045334,
          "rmse": 0.31970775916467775
        },
        "ridge": {
          "bias": -0.00632938468657649,
          "mae": 0.21086091609621913,
          "r_squared": 0.9606611907242005,
          "rmse": 0.3061741627427641
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.8846153846153846
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.29393292787014164
    },
    "delta_total_soc_t_c_ha|120": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.4706734114147364,
        "policy_mean": {
          "bias": -0.14306608122253198,
          "mae": 0.25215112968383735,
          "r_squared": 0.9852120898726925,
          "rmse": 0.35347945129252484
        },
        "ridge": {
          "bias": -0.06436859396854708,
          "mae": 0.2562040825523845,
          "r_squared": 0.9872487615399324,
          "rmse": 0.3282365616691788
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.8333333333333334
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.4706734114147364,
        "policy_mean": {
          "bias": 0.08288227128588464,
          "mae": 0.20278620885150117,
          "r_squared": 0.9792594501503555,
          "rmse": 0.36783975291588894
        },
        "ridge": {
          "bias": 0.029458696480206645,
          "mae": 0.21836193380409774,
          "r_squared": 0.9809641419284157,
          "rmse": 0.35239907387802977
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.875
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.2679741846292093
    },
    "delta_total_soc_t_c_ha|60": {
      "acceptable_ood": true,
      "beats_policy_mean_on_test": true,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.4337648780286454,
        "policy_mean": {
          "bias": -0.074461715637841,
          "mae": 0.22418968951975815,
          "r_squared": 0.9668730932623493,
          "rmse": 0.30082302733988786
        },
        "ridge": {
          "bias": -0.0023540930590499267,
          "mae": 0.2352233846133117,
          "r_squared": 0.9689832834701313,
          "rmse": 0.29108414153758394
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.9166666666666666
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.4337648780286454,
        "policy_mean": {
          "bias": 0.04326514622214891,
          "mae": 0.1579177824979911,
          "r_squared": 0.96997692502971,
          "rmse": 0.25482732106765665
        },
        "ridge": {
          "bias": 0.006772254373058535,
          "mae": 0.1685789464724776,
          "r_squared": 0.9728483473580194,
          "rmse": 0.24233522025532042
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.8846153846153846
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.2633174460173601
    },
    "delta_yield_t_dm_ha|24": {
      "acceptable_ood": false,
      "beats_policy_mean_on_test": false,
      "ood": {
        "empirical_location_count": 4,
        "interval_half_width": 0.09560113308358609,
        "policy_mean": {
          "bias": -0.011296194199452372,
          "mae": 0.02715214535627283,
          "r_squared": 0.6787770315726969,
          "rmse": 0.061896232278149416
        },
        "ridge": {
          "bias": -0.030571283794282072,
          "mae": 0.04062071994037629,
          "r_squared": 0.5931810880942435,
          "rmse": 0.06965647372171828
        },
        "row_count": 24,
        "validation_calibrated_90_percent_interval_coverage": 0.875
      },
      "selected_alpha": 0.1,
      "test": {
        "empirical_location_count": 11,
        "interval_half_width": 0.09560113308358609,
        "policy_mean": {
          "bias": 0.008045456613633501,
          "mae": 0.026858034909935106,
          "r_squared": 0.5066115407101088,
          "rmse": 0.05502899471148449
        },
        "ridge": {
          "bias": -0.004149027400521744,
          "mae": 0.03979410371217752,
          "r_squared": 0.49732407650242005,
          "rmse": 0.055544508463642374
        },
        "row_count": 104,
        "validation_calibrated_90_percent_interval_coverage": 0.8653846153846154
      },
      "uncertainty_calibrated": true,
      "validation_rmse": 0.0667332328376664
    }
  }
}
