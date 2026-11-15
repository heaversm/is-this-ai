# Provenance check — results

363 images: AI originals 60, AI re-shared 119, real originals 60, real re-shared 124.

The bar: right at least 80% of the time when it gives an answer.

## The combined display

- **Confirmed:** metadata, a signed label, or Google's watermark says so.
- **Likely:** detector `haywoodsloan_swinv2` is at least 0.95 confident. It's the detector that answered most often while staying above 80% when tested on images it wasn't tuned on.
- **Don't know:** everything else.

**Original files**

| Level | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Confirmed | 12/120 (10%) | 100% (76%–100%) | 0 |
| Likely | 93/120 (78%) | 87% (79%–92%) | 5 |
| Don't know | 15/120 (12%) | | |

**Re-shared copies**

| Level | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Confirmed | 0/243 (0%) | — | 0 |
| Likely | 215/243 (88%) | 78% (72%–83%) | 0 |
| Don't know | 28/243 (12%) | | |

**All images**

| Level | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Confirmed | 12/363 (3%) | 100% (76%–100%) | 0 |
| Likely | 308/363 (85%) | 81% (76%–85%) | 5 |
| Don't know | 43/363 (12%) | | |

**By where the images came from**

| Where from | Images | Confirmed | Likely | Don't know | Wrong answers |
|---|---|---|---|---|---|
| factcheck | 123 | 0 | 108 | 15 | 39 |
| simulated | 120 | 0 | 107 | 13 | 9 |
| wikimedia | 120 | 12 | 93 | 15 | 12 |

*The Likely cutoff here was picked on all images, which flatters it a little. The cross-validated detector table further down is the fairer number.*

## Each check on its own

**Original files**

| Check | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Metadata and signed labels | 11/120 (9%) | 100% (74%–100%) | 0 |
| Google watermark (Gemini) | 1/120 (1%) | 100% (21%–100%) | 0 |
| Detector `ateeqq_siglip`, always answers | 120/120 (100%) | 88% (81%–93%) | 6 |
| Detector `haywoodsloan_swinv2`, always answers | 120/120 (100%) | 87% (79%–92%) | 7 |
| Detector `organika_sdxl`, always answers | 120/120 (100%) | 69% (60%–77%) | 14 |
| Detector `commfor_vit384`, always answers | 120/120 (100%) | 78% (70%–85%) | 1 |

**Re-shared copies**

| Check | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Metadata and signed labels | 0/243 (0%) | — | 0 |
| Google watermark (Gemini) | 0/243 (0%) | — | 0 |
| Detector `ateeqq_siglip`, always answers | 243/243 (100%) | 73% (67%–78%) | 29 |
| Detector `haywoodsloan_swinv2`, always answers | 243/243 (100%) | 75% (70%–80%) | 3 |
| Detector `organika_sdxl`, always answers | 243/243 (100%) | 65% (59%–71%) | 34 |
| Detector `commfor_vit384`, always answers | 243/243 (100%) | 65% (59%–71%) | 0 |

**All images**

| Check | Answered | Right when it answered (95% range) | Real photos called AI |
|---|---|---|---|
| Metadata and signed labels | 11/363 (3%) | 100% (74%–100%) | 0 |
| Google watermark (Gemini) | 1/363 (0%) | 100% (21%–100%) | 0 |
| Detector `ateeqq_siglip`, always answers | 363/363 (100%) | 78% (74%–82%) | 35 |
| Detector `haywoodsloan_swinv2`, always answers | 363/363 (100%) | 79% (75%–83%) | 10 |
| Detector `organika_sdxl`, always answers | 363/363 (100%) | 66% (61%–71%) | 48 |
| Detector `commfor_vit384`, always answers | 363/363 (100%) | 70% (65%–74%) | 1 |

## Detectors, answering only when confident

The cutoff is the lowest confidence that was right 80% of the time on half the images. It's then measured on the other half, and the halves are swapped. Needs at least 10 answers in a half to pick a cutoff.

**Original files**

| Check | Answered | Right when it answered (95% range) | Real photos called AI | Cutoffs chosen |
|---|---|---|---|---|
| `ateeqq_siglip` | 120/120 (100%) | 88% (81%–93%) | 6 | [0.5, 0.5] |
| `haywoodsloan_swinv2` | 120/120 (100%) | 87% (79%–92%) | 7 | [0.5, 0.5] |
| `organika_sdxl` | 50/120 (42%) | 74% (60%–84%) | 3 | [None, 0.98] |
| `commfor_vit384` | 118/120 (98%) | 78% (70%–84%) | 1 | [0.7, 0.5] |

**Re-shared copies**

| Check | Answered | Right when it answered (95% range) | Real photos called AI | Cutoffs chosen |
|---|---|---|---|---|
| `ateeqq_siglip` | too few images, or never reached 80% | | | [None, None] |
| `haywoodsloan_swinv2` | 108/243 (44%) | 75% (66%–82%) | 0 | [0.95, None] |
| `organika_sdxl` | too few images, or never reached 80% | | | [None, None] |
| `commfor_vit384` | too few images, or never reached 80% | | | [None, None] |

**All images**

| Check | Answered | Right when it answered (95% range) | Real photos called AI | Cutoffs chosen |
|---|---|---|---|---|
| `ateeqq_siglip` | 182/363 (50%) | 76% (70%–82%) | 16 | [None, 0.5] |
| `haywoodsloan_swinv2` | 315/363 (87%) | 80% (75%–84%) | 7 | [0.5, 0.99] |
| `organika_sdxl` | too few images, or never reached 80% | | | [None, None] |
| `commfor_vit384` | too few images, or never reached 80% | | | [None, None] |

## Wrong answers, to read one by one

| File | Level | Said | Why | Where from |
|---|---|---|---|---|
| `ai/direct/wm_DALL-E-The-last-human-on-earth-after-a-major-apoca-7bc9a6.jpg` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:DALL.E_The_last_human_on_earth_after_a_major_apocalypse.jpg |
| `ai/direct/wm_Dise-o-de-aulas-virtuales-742b34.jpg` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Diseño_de_aulas_virtuales.jpg |
| `ai/direct/wm_Harmoni-i-musikk.png` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Harmoni_i_musikk.png |
| `ai/direct/wm_Nano-Banana-Chalk-Rhino-111e94.png` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Nano_Banana_-_Chalk_Rhino.png |
| `ai/direct/wm_Nano-Banana-Crayon-Rhino-95028b.png` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Nano_Banana_-_Crayon_Rhino.png |
| `ai/direct/wm_Red-lightsaber-luming-the-foggy-dark-965cba.png` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Red_lightsaber_luming_the_foggy_dark.png |
| `ai/direct/wm_Window-with-lugsill.png` | Likely | real | detector `haywoodsloan_swinv2` | wikimedia:ai-category https://commons.wikimedia.org/wiki/File:Window_with_lugsill.png |
| `ai/reshared/fc_aramco-tower-riyadh.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/11/fact-check-image-of-aramco-tower-in-riyadh-does-not-show-real-damage-after-houthi-attack.html |
| `ai/reshared/fc_bengali-woman-1903.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/06/fact-check-fake-photo-labeled-with-recycled-caption-bengali-woman-carrying-a-british-merchant-and-dated-1903-was-made-with-openai-tools.html |
| `ai/reshared/fc_blue-angels-beach-flyover.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/07/fact-check-fake-image-shows-blue-angels-flyover-on-florida-beach.html |
| `ai/reshared/fc_brics-summit-selfie.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/09/fact-check-russian-embassy-brics-summit-image-is-not-real-photo.html |
| `ai/reshared/fc_costco-texas-shoppers.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/costco-texas-muslim-customers-ai/ |
| `ai/reshared/fc_deniro-trump-tower.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/05/fact-check-fake-photo-robert-deniro-flipping-the-bird-trump-tower-obama-tshirt-its-ai.html |
| `ai/reshared/fc_disney-milton-flood.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2024/10/fact-check-images-of-disney-world-destroyed-by-hurricane-milton-are-not-authentic-its-ai-generated.html |
| `ai/reshared/fc_egyptian-cat-sculpture.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/egyptian-sculptures-cats/ |
| `ai/reshared/fc_eiffel-tower-hay-bales.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:fullfact https://fullfact.org/online/eiffel-tower-hay-bales-artifical-intelligence-image/ |
| `ai/reshared/fc_epstein-tel-aviv.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/02/fact-check-jeffrey-epstein-was-not-photographed-walking-in-tel-aviv-ai-generated-image.html |
| `ai/reshared/fc_f15-colonel-rescue-iran.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:politifact https://www.politifact.com/factchecks/2026/apr/06/social-media/American-Colonel-pilot-photos-AI-Iran/ |
| `ai/reshared/fc_idf-soldier-axe-statue.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/04/fact-check-image-of-axe-wielding-idf-soldier-beside-headless-christian-icon-is-an-ai-fake.html |
| `ai/reshared/fc_inflatable-jd-vance-white-house.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2025/10/fact-check-image-of-inflatable-jd-vance-as-part-of-2025-white-house-halloween-decorations-is-not-real-photo.html |
| `ai/reshared/fc_iran-bushehr-human-chain.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:fullfact https://fullfact.org/conflict/fake-picture-human-chain-power-plant-iran/ |
| `ai/reshared/fc_jamaica-hurricane-melissa-damage.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:fullfact https://fullfact.org/environment/jamaica-hurricane-melissa-photo-fake/ |
| `ai/reshared/fc_maduro-capture-dea.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:politifact https://www.politifact.com/factchecks/2026/jan/05/social-media/venezuela-maduro-artificial-intelligence-images/ |
| `ai/reshared/fc_malibu-1965-movie-stars-bbq.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/10/fact-check-fake-image-of-movie-stars-enjoying-a-barbecue-in-1965-malibu.html |
| `ai/reshared/fc_mcconnell-life-support.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/07/fact-check-fake-photo-of-mitch-mcconnell-on-life-support-was-generated-using-openai.html |
| `ai/reshared/fc_merz-epstein.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/09/fact-check-image-is-not-real-photo-of-merz-and-epstein.html |
| `ai/reshared/fc_netanyahu-whiteboard.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/10/fact-check-fake-photo-shows-netanyahu-in-front-of-whiteboard-plan-involving-spain-generated-with-openai.html |
| `ai/reshared/fc_ohio-rally-epstein-protester.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/image-ohio-trump-rally-protester/ |
| `ai/reshared/fc_plane-fire-cartel.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/02/fact-check-plane-fire-picture-after-cartel-leader-killing-is-ai-generated.html |
| `ai/reshared/fc_reflecting-pool-guard-towers.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/reflecting-pool-barbed-wire-towers/ |
| `ai/reshared/fc_rittenhouse-lil-wayne.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/07/fact-check-fake-image-of-kyle-rittenhouse-lil-wayne-was-made-with-ai.html |
| `ai/reshared/fc_seven-dogs-selfie.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/03/ffact-check-fake-selfie-of-seven-dogs-walking-together-in-china-is-not-real-photo.html |
| `ai/reshared/fc_spiderman-jake-lang-fake.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/08/fact-check-fake-image-shows-spider-man-punching-jake-lang-at-a-minneapolis-protest.html |
| `ai/reshared/fc_tall-ships-liberty-island.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/07/fact-check-fake-image-does-not-show-real-tall-ships-sailing-near-liberty-island.html |
| `ai/reshared/fc_troops-reptilians.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/10/fact-check-fake-image-of-us-troops-shooting-reptilians-is-not-real-photo.html |
| `ai/reshared/fc_trump-bowing-xi.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/05/fact-check-fake-photo-shows-trump-bowing-to-xi-as-they-shake-hands.html |
| `ai/reshared/fc_trump-butler-ear-car.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/trump-ear-image-assassination/ |
| `ai/reshared/fc_trump-epstein-shirtless-boat.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/image-trump-epstein-shirtless-boat/ |
| `ai/reshared/fc_trump-musk-huang-ccp-fists.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/05/fact-check-fake-photo-shows-trump-musk-and-huang-raising-their-fists-in-front-of-chinese-flag-joining-communist-party.html |
| `ai/reshared/fc_trump-nordic-aliens.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:snopes https://www.snopes.com/fact-check/trump-nordic-aliens-images/ |
| `ai/reshared/fc_trump-stairs-struggle.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:politifact https://www.politifact.com/article/2026/apr/06/Donald-Trump-health-Walter-Reed/ |
| `ai/reshared/fc_trump-xi-state-dinner.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/09/fact-check-fake-photo-trump-state-dinner-xi-elon-musk-jeff-bezos-head-table-ai-generated.html |
| `ai/reshared/fc_us-soldiers-captured-iran.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:fullfact https://fullfact.org/conflict/captured-us-soldiers-iran-image-fake/ |
| `ai/reshared/fc_von-der-leyen-epstein.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/09/fact-check-fake-photo-ursula-von-der-leyen-jeffrey-epstein-ai.html |
| `ai/reshared/fc_walmart-trump-merch-clearance.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2025/11/fact-check-photo-of-walmart-clearance-sale-of-trump-merch-is-not-real.html |
| `ai/reshared/fc_wilson-joseph-capture.jpg` | Likely | real | detector `haywoodsloan_swinv2` | factcheck:leadstories https://leadstories.com/hoax-alert/2026/11/fact-check-fake-image-showing-capture-of-wilson-joseph-was-made-with-google-ai.html |
| `ai/reshared/rs_chat_wm_Harmoni-i-musikk.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:chat copy of ai/direct/wm_Harmoni-i-musikk.png |
| `ai/reshared/rs_chat_wm_Nano-Banana-Crayon-Rhino-95028b.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:chat copy of ai/direct/wm_Nano-Banana-Crayon-Rhino-95028b.png |
| `ai/reshared/rs_chat_wm_Red-lightsaber-luming-the-foggy-dark-965cba.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:chat copy of ai/direct/wm_Red-lightsaber-luming-the-foggy-dark-965cba.png |
| `ai/reshared/rs_screenshot_wm_ChaoticHarmony-explosion-in-post-painter-abstraction-Nano-Ba.png` | Likely | real | detector `haywoodsloan_swinv2` | simulated:screenshot copy of ai/direct/wm_ChaoticHarmony-explosion-in-post-painter-abstraction-Nano-Ba.webp |
| `ai/reshared/rs_screenshot_wm_Dise-o-de-aulas-virtuales-742b34.png` | Likely | real | detector `haywoodsloan_swinv2` | simulated:screenshot copy of ai/direct/wm_Dise-o-de-aulas-virtuales-742b34.jpg |
| `ai/reshared/rs_screenshot_wm_Window-with-lugsill.png` | Likely | real | detector `haywoodsloan_swinv2` | simulated:screenshot copy of ai/direct/wm_Window-with-lugsill.png |
| `ai/reshared/rs_social_wm_DALL-E-The-last-human-on-earth-after-a-major-apoca-7bc9a6.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:social copy of ai/direct/wm_DALL-E-The-last-human-on-earth-after-a-major-apoca-7bc9a6.jpg |
| `ai/reshared/rs_social_wm_Nano-Banana-Chalk-Rhino-111e94.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:social copy of ai/direct/wm_Nano-Banana-Chalk-Rhino-111e94.png |
| `ai/reshared/rs_social_wm_Ranis-the-LRJ-and-other-MPUP-transitional-technoco-2b108e.jpg` | Likely | real | detector `haywoodsloan_swinv2` | simulated:social copy of ai/direct/wm_Ranis-the-LRJ-and-other-MPUP-transitional-technoco-2b108e.jpg |
| `real/direct/wm_Alfa-Romeo-Spider-4-Travelarz-df4159.jpg` | Likely | ai | detector `haywoodsloan_swinv2` | wikimedia:random-camera-photo https://commons.wikimedia.org/wiki/File:Alfa_Romeo_Spider_(4)_Travelarz.JPG |
| `real/direct/wm_Bus-SitpC-Bog-abr-2018-3e4419.jpg` | Likely | ai | detector `haywoodsloan_swinv2` | wikimedia:random-camera-photo https://commons.wikimedia.org/wiki/File:Bus_SitpC_Bog_abr_2018.jpg |
| `real/direct/wm_Klosterkirche-Heilig-Kreuz-Donauw-rth-Innenraum-1-03df35.jpg` | Likely | ai | detector `haywoodsloan_swinv2` | wikimedia:random-camera-photo https://commons.wikimedia.org/wiki/File:Klosterkirche_Heilig_Kreuz_(Donauwörth)_Innenraum_1.jpg |
| `real/direct/wm_New-York-City-i-i-29598865920-5bfe30.jpg` | Likely | ai | detector `haywoodsloan_swinv2` | wikimedia:random-camera-photo https://commons.wikimedia.org/wiki/File:New_York_City_-_-i---i-_(29598865920).jpg |
| `real/direct/wm_Volkswagen-Clasico-Front-5b6d9f.jpg` | Likely | ai | detector `haywoodsloan_swinv2` | wikimedia:random-camera-photo https://commons.wikimedia.org/wiki/File:Volkswagen_Clasico_--_Front.JPG |
