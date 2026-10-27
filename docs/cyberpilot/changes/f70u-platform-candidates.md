# F70U Hyundai Platform Catalog and Owner Binding

Source: [pinned opendbc definitions](https://github.com/commaai/opendbc/blob/4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76/opendbc/car/hyundai/values.py#L296).
Machine map: artifacts/f70u/F70U_PLATFORM_CANDIDATES.json.

| Catalog ID | Documented years | Distinction | Owner-bound |
| --- | --- | --- | --- |
| HYUNDAI_SANTA_FE | 2019-20 | earlier catalog range | no |
| HYUNDAI_SANTA_FE_2022 | 2021-23 | non-hybrid catalog alias; diesel/region/trim not proved | no |
| HYUNDAI_SANTA_FE_HEV_2022 | 2022-23 | hybrid; differs from owner diesel description | no |
| HYUNDAI_SANTA_FE_PHEV_2022 | 2022-23 | plug-in hybrid; differs from owner diesel description | no |

These four records are not merged. Their static class is classic CAN; this is not a finding about the owner's actual vehicle.
No actual fingerprint, firmware payload, CAN data or vehicle observation was collected or matched.
FW_VERSIONS defines multiple regional TM/TMA signatures; it cannot identify an unknown vehicle from marketing description.
SCC origin, HDA generation, safetyParam and dynamic-detection flags remain unbound.
The source configures torque tuning, but mode deployment and production-stage equivalence remain unapproved.
