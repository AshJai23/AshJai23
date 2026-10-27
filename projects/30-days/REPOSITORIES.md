# Separate project repositories

Requested on 27 October 2026. **Creation/publication is pending**: the connected
GitHub actions do not include repository creation. No destination below is linked
as a website or claimed to exist. Existing source folders remain accessible.

| Project | Requested repository name | Niche | State |
|---|---|---|---|
| 01 | `ds-01-live-earthquake-analytics` | Hazard awareness and local weather exposure | Prepared for extraction; not published |
| 02 | `ds-02-carbon-intensity-forecast` | GB energy and council carbon reporting | Prepared for extraction; not published |
| 03 | `ds-03-weather-quality-monitor` | Weather-feed quality for transport and operations | Prepared for extraction; not published |
| 04 | `ds-04-bike-availability-forecast` | Bike-share operations and station rebalancing | Prepared for extraction; not published |
| 05 | `ds-05-air-quality-spatial-analytics` | London council environmental reporting | Prepared for extraction; not published |
| 06 | `ds-06-rss-topic-clustering` | Science and technology headline organisation | Prepared for extraction; not published |
| extra-student | `uk-student-copilot` | UK international-student support: reviewed GOV.UK source cards and a trained local routing head; not a live legal adviser. | Prepared for extraction; not published |

[All 44 sprint destinations and the extra Student Copilot](REPOSITORIES.json).
Future repositories will be created only when they contain a built project.
Extraction does not change the sprint count: **6/44 complete**.

The repository export must include all source files, tests, data provenance,
existing measured results and a source commit pointer. Rerun tests and a saved
replay from each new project root, fix root-relative commands/links, publish,
and verify its destination tree before updating the profile links.

Extraction verification: **133 original files checked against Git blob hashes;
130 tests passed; six saved-source CLI replay smoke runs passed**.
[Evidence](migration-validation.json) · [Actual logs](migration-validation.txt).
Student Copilot tests mocked model proposals; Qwen inference was not rerun.
