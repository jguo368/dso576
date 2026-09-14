Candidate Vision A
A Medi-Cal workforce planning manager at the California Department of Health Care Services must decide which counties and provider specialties should be prioritized for provider recruitment support.
Candidate Vision B
A Medi-Cal access strategy manager at the California Department of Health Care Services must decide which counties and population groups should be prioritized for language-capacity, telehealth, or transportation support.
Source and Access
The core data source is the Profile of Enrolled Medi-Cal Fee-for-Service (FFS) Providers, published by the California Department of Health Care Services (DHCS). The dataset is publicly accessible and licensed for public use. It is available through the California Open Data Portal in CSV format, with additional provider type and specialty reference files. The dataset is based on the Medi-Cal Provider Master File and contains information on providers enrolled in Medi-Cal Fee-for-Service.
Possible supplemental sources are also publicly available. The Medi-Cal Certified Eligibles Data by Month with Demographics is published by DHCS with public access under a Creative Commons Attribution license. The Medi-Cal Managed Care Enrollment Report is also published by DHCS and publicly available in CSV format. The HCAI Health Workforce Data portal is maintained by the California Department of Health Care Access and Information and provides additional workforce-related data and dashboards.
Available Data
The core Medi-Cal FFS provider dataset contains basic provider information including provider number, provider name, provider type, specialty, and geographic information. It also includes separate provider type and specialty code reference files. The dataset represents providers enrolled in Medi-Cal Fee-for-Service and does not include Medi-Cal Managed Care providers. 
The Medi-Cal Certified Eligibles dataset contains monthly county-level Medi-Cal eligibility data split across multiple demographic dimensions. Available CSV files include data by age group and sex, aid category, delivery system and plan, Medicare dual status, primary language, and race/ethnicity and age group. These files are separated rather than distributed as a single dataset for de-identification purposes. 
The Medi-Cal Managed Care Enrollment Report contains the total number of Medi-Cal managed care enrollees by reported month, plan type, county, and health plan. 
HCAI also provides health workforce information that may support analysis of geographic workforce distribution, provider supply, workforce shortages, and language capacity.
Scale
The core provider source contains multiple downloadable resources, including the main FFS provider CSV, provider type reference data, provider specialty reference data, and ZIP downloads. It is updated regularly and reflects a point-in-time snapshot of enrolled FFS providers. 
The Medi-Cal demographic source contains 12 available resources, including multiple CSV files and a combined ZIP file. Because the demographic information is already divided by topic, the team can initially work only with the specific files relevant to the project rather than downloading all resources. 
The managed-care enrollment source is smaller in structure, with a CSV resource and a ZIP download. 
At this stage, the available sources appear suitable for initial work using flat files such as CSV and Python/pandas. A database is not necessary unless later analysis shows that the scale, number of related tables, or repeated shared queries justify one. This follows the course guidance to begin with the smallest workable source rather than immediately installing a database or downloading all available data. 
First Access Test
We confirmed that the core Medi-Cal FFS provider source is publicly listed with downloadable CSV resources and contains provider enrollment, specialty, and geographic information. We also confirmed that the Medi-Cal Certified Eligibles source provides downloadable demographic CSV files, including a primary-language file, and that the Managed Care Enrollment Report is available as a downloadable CSV. 
For the next small access test, the team can load the main provider CSV or a small portion of it in Python/pandas and inspect the first several rows to confirm the exact column structure and what one row represents. The team can then repeat the same small test with one demographic file, such as the primary-language dataset, before attempting any larger integration.
Vision A Technical Path
Vision A requires data that can identify differences in provider capacity by county and specialty. The core FFS provider dataset is promising because it includes provider specialty and geographic information. Medi-Cal enrollment or eligible-population data can then provide a denominator for comparing provider availability across counties.
A likely technical approach is to aggregate provider records by geography and specialty and connect those summaries to Medi-Cal population or enrollment counts using compatible geographic fields such as county. Before doing this, the team needs to confirm the exact geographic fields in the provider dataset and whether they align cleanly with county identifiers in the enrollment datasets.
Vision B Technical Path
Vision B requires additional information beyond basic provider counts because it focuses on language capacity, telehealth, and transportation support. The Medi-Cal demographic dataset is promising for language-related analysis because it contains a specific file for certified eligibles by primary language. 
HCAI workforce data may also provide useful workforce and geographic information for evaluating provider availability and access. However, the team still needs to verify which specific downloadable fields are available at a compatible geographic level and whether telehealth-related or language-capacity variables can be directly linked to Medi-Cal provider or beneficiary data. 
Transportation access is less directly represented in the sources identified so far, so an additional geographic or transportation source may be required if the team ultimately selects that component of Vision B.
Blockers / Next Checks
The main remaining technical questions are:
Confirm the exact columns and row structure of the main Medi-Cal FFS provider CSV.
Confirm which geographic variable can be used consistently across provider, eligibility, and managed-care enrollment data.
Check whether provider specialty codes can be mapped cleanly using the provided specialty reference file.
Determine whether HCAI provides sufficiently detailed public data on language capacity or telehealth availability.
Determine whether Vision B would require an additional transportation or travel-access dataset.
Check how the fact that the core provider profile covers Fee-for-Service providers only, not Managed Care providers, affects the technical design of both visions. 
Possible Technical Approach
For the initial stage, the team can work with CSV files using Python and pandas. The project can begin by loading only the smallest relevant files, inspecting their columns and row structure, and testing whether they can be joined using geography and other shared variables. PostgreSQL or another database should only be considered later if the data becomes too large or relationally complex for convenient flat-file analysis. Streamlit may eventually be useful for an interactive provider-capacity planning interface, but deployment is not required at this stage.

