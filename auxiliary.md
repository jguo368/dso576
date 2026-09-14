Candidate Vision A

A Medi-Cal workforce planning manager at the California Department of Health Care Services must decide which counties and provider specialties should be prioritized for provider recruitment support.

Candidate Vision B
A Medi-Cal access strategy manager at the California Department of Health Care Services must decide which counties and underserved population groups should be prioritized for language-access, telehealth, or transportation support.
Auxiliary Data Investigation
Candidate Vision A: HCAI Health Workforce Data
Decision-important information missing from the core data
The core Medi-Cal fee-for-service provider profile identifies providers enrolled in Medi-Cal FFS, but an enrolled provider is not necessarily equivalent to an actively practicing provider with available appointment capacity. To prioritize provider recruitment, the team also needs evidence about the broader healthcare workforce in each county, including workforce supply by specialty, geographic distribution, practice activity, and potentially expected retirements.
Without this information, a county could appear to have a shortage of Medi-Cal providers even though it has a relatively large overall workforce whose members do not participate in Medi-Cal. Conversely, a county’s enrolled-provider count could overstate practical capacity if some providers work limited clinical hours, primarily offer telehealth, are approaching retirement, or are not actively accepting Medi-Cal patients.
Proposed auxiliary source
The proposed addition is the California Department of Health Care Access and Information Health Workforce Data.
HCAI’s Health Workforce Research Data Center works with state licensing boards, the Employment Development Department, and higher-education entities to collect information about California’s healthcare workforce. HCAI states that its workforce information includes current worker supply and geographic distribution by specialty. Its licensure-renewal collection also includes fields such as:
Area of practice or specialty
City, county, and ZIP code of practice
National Provider Identifier
Direct patient-care hours
Telehealth hours
Languages spoken
Anticipated retirement year
Employer or primary-practice-site type
HCAI provides public reports, dashboards, and selected aggregate datasets, while individual-level information that could identify a professional is not publicly released.
Depending on the specific public HCAI dataset selected, one row would likely represent an aggregated workforce count for a particular profession or specialty, geographic area, and reporting period. This proposed row definition must be confirmed by opening the selected dataset and reviewing its documentation before analysis.
Likely fields
Potentially useful fields include:
County or ZIP code
Profession or specialty
Number of licensed professionals
Practice status or setting
Direct patient-care hours
Telehealth hours
Languages spoken
Reporting year
Expected retirement period
Not all these fields are guaranteed to appear together in one publicly downloadable file. The exact public fields and level of aggregation remain to be verified.
How it could connect to the core data
The HCAI data could be connected to the Medi-Cal FFS provider profile using shared geographic and professional categories, such as:
County
ZIP code
Provider profession
Provider specialty
Reporting year
If a public HCAI product includes usable National Provider Identifiers, an NPI-based match may also be explored. However, the public data may only be available in aggregate form, in which case the team would compare county-specialty totals rather than linking individual providers.
One possible output would be a county-specialty comparison containing:
Medi-Cal FFS enrolled-provider count
Overall active-workforce count
Medi-Cal eligible population
Enrolled Medi-Cal providers per 10,000 eligible residents
Overall workforce professionals per 10,000 eligible residents
Difference between general workforce availability and Medi-Cal participation
What could fail
Several issues could prevent a reliable connection:
HCAI and DHCS may use different specialty classifications.
One source may report practice location while another reports mailing or enrollment address.
The datasets may cover different reporting periods.
Public HCAI data may be aggregated and therefore unavailable for individual NPI matching.
Licensure does not prove that a provider is actively practicing or accepting new patients.
Medi-Cal enrollment does not prove that a provider currently treats Medi-Cal patients or has appointment capacity.
Suppression or aggregation for privacy could reduce detail in counties with small workforces.
Providers practicing at multiple locations could be counted differently across sources.
The team should therefore describe the resulting measure as an indicator of potential provider capacity, not as a direct measurement of appointment availability.
New question this addition would make answerable
This addition could help answer:
Which county-specialty combinations have both a low supply of Medi-Cal FFS providers relative to the eligible population and a low overall healthcare workforce supply?
It could also distinguish between two policy situations:
A general workforce shortage that may require recruitment or training support
A Medi-Cal participation gap in an area that otherwise has an adequate workforce
Synthetic fallback
If a suitable HCAI extract cannot be accessed, the team could create a clearly labeled synthetic table containing:
county, specialty, active_workforce_count, direct_care_hours, expected_retirements

The table could contain five fictional counties and three specialties. It would demonstrate how the core and auxiliary datasets could be joined and how county-specialty priority scores might be calculated. The synthetic results would be presented only as a prototype and not as evidence about actual California counties.

Candidate Vision B: Medi-Cal Certified Eligibles by Primary Language
Decision-important information missing from the core data
The core provider profile does not establish how many Medi-Cal-eligible residents in each county primarily use a language other than English. This information is necessary to determine where language-capacity support may be most needed.
Provider counts alone cannot show whether the linguistic capacity of the available provider network matches the language needs of the population. A county could have a relatively large number of providers but still have an access problem if too few providers or support services can communicate with major language groups.
Proposed auxiliary source
The proposed addition is the Medi-Cal Certified Eligibles Data by Month with Demographics, published by the California Department of Health Care Services.
DHCS describes this dataset as monthly county-level counts of Medi-Cal certified eligibles separated across multiple demographic files for de-identification. Available CSV resources include breakdowns by:
Primary language
Age group and sex
Race/ethnicity and age group
Aid category
Delivery system and plan
Medicare dual status
For this Vision, the most relevant resource is By Primary Language, Certified Eligibles.
One row is expected to represent the number of certified Medi-Cal eligibles associated with a particular county, reporting month, and primary-language category. The exact row structure and column names must be confirmed from the downloaded CSV before analysis.
Likely fields
The primary-language resource is likely to contain fields such as:
Reporting month or year
County
Primary-language category
Number of certified eligibles
The demographic traits are published in separate files rather than as one person-level dataset. Therefore, language generally cannot be cross-tabulated freely with age, race/ethnicity, or other characteristics unless DHCS publishes that combination.
How it could connect to the core data
The language dataset could be aggregated to the county level and connected to the provider profile primarily by county and compatible reporting period.
The team could calculate:
Total certified eligibles by county
Certified eligibles by primary language
Percentage of eligibles in each language group
Number or percentage of residents using a non-English primary language
Medi-Cal FFS providers per 10,000 certified eligibles
Counties with both limited provider capacity and substantial language-access needs
If provider-language information later becomes available from HCAI or another verified source, the team could compare patient language needs with provider language capacity. Without that provider-language information, the DHCS eligibility dataset can identify population need but cannot directly measure whether the provider network satisfies that need.
What could fail
Potential limitations include:
County names or geographic codes may require standardization before joining.
The provider and eligibility files may cover different dates.
“Certified eligibles” may not be identical to actual healthcare users or active managed-care members.
A recorded primary language does not fully measure interpretation needs or English proficiency.
Missing, unknown, or suppressed language values could affect county comparisons.
County-level aggregation can hide substantial differences among neighborhoods.
Because demographic traits are distributed in separate files, the team may not be able to identify combined groups such as older adults within a specific language category.
This source does not directly measure broadband access, transportation barriers, appointment availability, or telehealth readiness.
Counts alone do not prove that language barriers caused lower healthcare access.
This auxiliary source therefore supports the language-capacity portion of Vision B more directly than its telehealth or transportation portions. The team may need to narrow Vision B or add a different verified source later if it wants to compare all three interventions.
New question this addition would make answerable
This addition could help answer:
Which counties have the largest numbers or proportions of Medi-Cal certified eligibles in major non-English primary-language groups, especially when compared with local provider availability?
It could support prioritizing counties for further investigation or language-access resources. It would not, by itself, prove that a specific county has inadequate interpretation services.
Synthetic fallback
If the language file cannot be accessed or connected successfully, the team could create a clearly labeled synthetic dataset containing:
month, county, primary_language, certified_eligible_count

The prototype could use five fictional counties and several language categories. It could demonstrate how the team would calculate language-group shares and combine them with county-level provider counts. The values would be explicitly labeled as simulated and would not be used to make claims about real Medi-Cal populations.

Comparison of the Two Additions
Candidate
Missing input addressed
Proposed addition
Connection to core data
New analytical value
Vision A
Broader active workforce supply and geographic distribution by specialty
HCAI Health Workforce Data
County, ZIP code, specialty, year, and possibly NPI
Distinguishes general workforce shortages from possible Medi-Cal participation gaps
Vision B
Number and proportion of Medi-Cal eligibles by primary language
DHCS Certified Eligibles by Primary Language
County and reporting period
Identifies counties with potentially high language-access needs relative to provider availability

Verified Evidence
DHCS publishes monthly county-level Medi-Cal certified-eligible data separated into demographic resources, including primary language, age and sex, race/ethnicity and age, aid category, delivery system and plan, and Medicare dual status.
The demographic files are separated rather than distributed as a single person-level dataset for de-identification.
HCAI’s Health Workforce Research Data Center collects information concerning workforce supply, geographic distribution, specialties, direct patient-care hours, telehealth hours, languages spoken, practice location, and other workforce characteristics.
HCAI makes reports, dashboards, and selected data products publicly available but does not release identifiable raw individual-level workforce data.
Hypotheses Requiring Verification
The selected HCAI public extract can be aligned with the provider profile using county and specialty.
The HCAI resource provides a usable active-workforce count for every specialty included in the Medi-Cal provider data.
The primary-language CSV uses county and month fields compatible with the core data.
Low provider-to-eligible ratios are meaningful indicators of potential access pressure.
Counties with large non-English-language populations have insufficient matching provider-language capacity.
These are analytical hypotheses to investigate and should not be presented as confirmed facts.
Remaining Questions
What does one row represent in the exact version of the core Medi-Cal FFS provider profile?
Which location and specialty fields are shared across the DHCS provider data and HCAI workforce products?
Does the public HCAI data provide downloadable county-specialty counts, or only dashboards and shortage-area products?
Do the datasets cover compatible reporting periods?
Can any source establish whether an enrolled provider is actively accepting Medi-Cal patients?
Is reliable provider-language information available at the county level?
Should Vision B be narrowed to language access if comparable telehealth and transportation data cannot be located?

Sources
California DHCS: Medi-Cal FFS Provider Profile
California DHCS: Medi-Cal Certified Eligibles Data by Month with Demographics
California HCAI: Health Workforce Data
