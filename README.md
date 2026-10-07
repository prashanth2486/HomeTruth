# HomeTruth

A buyer-side web app that tells a home buyer if a Bengaluru listing is fairly priced, what it will really cost, whether they can afford it, and how the commute looks. An assistant explains those figures and nothing else.

Buyers cannot tell whether an asking price is fair, and they are surprised by stamp duty, registration, GST, and interest. Most property sites are paid by sellers and builders. HomeTruth is built for the person writing the cheque.

This is an estimate. It is not an official valuation, a loan offer, or legal advice.

## What you can do

- Search Bengaluru neighbourhoods on a map and open historical asks that the model has already scored.
- See a price range from the 10th to the 90th percentile, plus a mid estimate.
- Get a verdict: great deal, fair, or overpriced, and a suggested offer (40th to 60th percentile).
- Read the top three reasons in one sentence.
- Add stamp duty, registration, GST on an under-construction home, and loan interest.
- Compare buying with renting over 5, 10, and 15 years. Every assumption is on the screen and can be changed.
- Check whether the EMI fits 40–50% of net income after existing EMIs.
- Put two or three listings side by side.
- Create a free account to sync a shortlist and loan numbers across visits.
- Score metro stations, schools, hospitals, and IT parks within 2 km, and estimate a drive to the office.
- Ask questions about that one result. The assistant cannot see your income.
- Download a PDF summary.

Browse without signing in. Income is never written to the prediction log. Signed-in users can sync loan numbers to their account; guests keep them in the browser tab only.

## Architecture

```
Catalog search / map (public)
Account (register / login / JWT) -> synced shortlist + optional buyer prefs
Listing + income + optional office
        |
        +-- LightGBM quantile models -> SHAP sentence, verdict, offer
        +-- Stamp duty, GST, EMI, affordability, buy vs rent
        +-- OpenStreetMap locality score and commute
        |
        v
   One analysis JSON
        |
        +-- FastAPI (also serves the React site)
        +-- Streamlit (old demo)
        +-- Claude, only when an API key is set, reading that JSON
```

## Metrics

Trained on the public Bengaluru house listings file (asking prices, in lakhs). After cleaning: 9,862 rows, 189 localities kept, rarer names grouped as `other`. The target is `log(price)`. There is no listing date, so there is no time split.

Validation is 5-fold `GroupKFold` on locality. A locality in the test fold is mapped to `other`, so the score is for areas the model did not see. A shuffled 5-fold is reported as well, because a buyer usually picks a known neighbourhood.

| Check | LightGBM median | Ridge baseline | 10th–90th coverage |
|---|---:|---:|---:|
| Unseen localities (grouped CV) | MAPE 25.9%, median error ₹13.0 lakh | MAPE 53.6%, median error ₹17.5 lakh | 80.8% |
| Known localities (random K-fold) | MAPE 19.2%, median error ₹9.0 lakh | median error ₹12.4 lakh | 74.1% |

The design target is about 80% of held-out asking prices inside the 10th–90th band. Grouped CV meets it. On known localities the band is a bit tight (74%). The linear baseline's mean percentage error on the random split is not a useful headline: a few `exp()` predictions blow up, while its median error stays in the same range as the table above.

These errors are on asking prices, not on registered sale prices. Expect individual homes to miss the band.

## How to run locally

Python 3.12 is the version this project is tested with.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py
python scripts/retrain.py
python scripts/build_catalog.py
cd web && npm install && npm run build && cd ..
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. That process serves the website and the API.

- `GET /localities?q=` search neighbourhoods
- `GET /localities/{name}` summary and listings
- `GET /localities/{name}/location` metro, schools, hospitals, and IT parks
- `GET /listings` filter by locality, BHK, verdict, and max price
- `GET /listings/{id}` one historical ask
- `GET /map` localities that have coordinates
- `GET /health`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `PUT /auth/me/shortlist`, `PUT /auth/me/buyer`
- `POST /analyze`
- `POST /compare` with 2 or 3 listings
- `POST /chat`
- `POST /report` returns the PDF

Accounts use bcrypt password hashes and JWT bearer tokens (7-day sessions). User rows live in `data/app.db` by default (SQLite). Set `HOMETRUTH_JWT_SECRET` in production.

The old Streamlit screen is still there if you want it: `streamlit run app/streamlit_app.py`.

The PDF is a POST so the analysis does not have to be stored and income is not placed in a URL.

Copy `.env.example` to `.env`. Set `HOMETRUTH_JWT_SECRET` for real deploys, and `ANTHROPIC_API_KEY` if you want the assistant to answer ordinary questions. Flood and “should I take this loan?” questions are refused even without a key. `ANTHROPIC_MODEL` defaults to `claude-sonnet-4-5`.

### Frontend only (optional)

For local UI work against an already running API:

```bash
cd web && npm install && npm run dev
```

Vite proxies API calls to `http://127.0.0.1:8000`. You can also build `web/dist` and let FastAPI serve it, or host the built assets on Netlify/Vercel/Cloudflare Pages and point the API origin at your Render/HF backend.

```bash
pytest
python scripts/drift_report.py
```

`models/hometruth.joblib`, `data/raw/`, and `data/catalog.json` are gitignored. `scripts/retrain.py` rebuilds the model. `scripts/build_catalog.py` scores every cleaned listing and writes the catalog the website searches. `models/metrics.json` is the scorecard above.

## Rates used in the calculator

Checked 7 October 2026. Confirm them before a purchase. They are in `src/rates.py` and on the screen.

- Stamp duty is 5% of the price. The first sale of a flat is 2% up to ₹20 lakh, 3% up to ₹45 lakh, and 5% above that. The rate applies to the whole price.
- Cess is 10% of the duty. The BBMP surcharge is 2% of the duty. Together with a 5% base, stamp duty is 5.6% of the price.
- Registration is 2% of the price from 31 August 2025 (notification RD/46/MNMU/2025).
- Duty is legally charged on the higher of the price and the guidance value. This app has no guidance values, and it says so.
- GST applies only to under-construction homes: 1% if carpet area is at most 60 sq m and the price is at most ₹45 lakh, otherwise 5%. If you do not enter carpet area, the app assumes 70% of the area you typed.
- The default loan rate is 8.0%, inside the SBI home-loan band of 7.25–8.55% reported for October 2026. Change it.

Rent is an indicative gross yield, 3% of the price a year unless `data/rent_yields.json` has a locality override or you type your own. It is not an observed rent.

The locality score weights metro 35, IT parks 25, schools 20, and hospitals 20. Each part is 0–100 from the count and the nearest place inside 2 km. IT parks are OpenStreetMap offices tagged `office=it` or named as a tech park, so that part is often low. Commute time is the shortest drive at 25 km/h. It ignores live traffic. Lookups are cached under `data/cache/`. If the map service fails, the price and the costs still come back.

## Deploy

There is no live URL yet. This repo cannot create a hosting account.

Hugging Face Spaces or Render: use the `Dockerfile`. The image builds the website, downloads the listings, trains the model, writes the catalog, and serves everything with uvicorn on port 8000.

A host that only runs the API can start with `uvicorn api.main:app --host 0.0.0.0 --port $PORT` after `pip install -r requirements.txt && python scripts/download_data.py && python scripts/retrain.py && python scripts/build_catalog.py`.

Set `ANTHROPIC_API_KEY` in the host's secret store, not in the image.

## Limitations

- The model learns asking prices, not prices people actually paid. If every seller in a locality overprices by the same amount, the model will call that normal.
- One city. No builder reputation, floor, facing, or legal status.
- Rent figures are weak. They are yields, labelled indicative.
- Commute time ignores live traffic.
- Some homes will miss the range by a lot. Unseen localities are grouped into `other` and marked as less reliable.
- Stamp duty ignores guidance value.
- The map score depends on OpenStreetMap being complete.

## Logging and retraining

Each analysis appends locality, size, and the predicted range to `data/logs/predictions.jsonl`. Income, office address, and the asking price are not logged. `python scripts/drift_report.py` prints how many predictions were logged, the median mid estimate, and the locality counts. When you have a newer listings file, replace `data/raw/Bengaluru_House_Data.csv` and run `python scripts/retrain.py`.

## Demo video

Record these shots, about two minutes:

1. The disclaimer at the top.
2. Analyze the Whitefield 2 BHK that is already filled in. Show the verdict, the range, and the sentence.
3. Scroll the cost breakdown, the EMI check, and the buy-versus-rent table. Change the interest rate and run it again.
4. Add a second listing and open Compare.
5. Ask “Is it safe from floods?” and “Should I take this loan?”.
6. Download the PDF and show the same disclaimer on the first page.

## Interview notes

**Why are asking prices biased?** Sellers advertise a price they hope to get. Homes that sell quietly, or not at all, may be missing. The model learns that advertised distribution. It can say whether a new ask is high or low next to other asks. It cannot see a market where every ask is high by the same margin, and it is not a valuation of what the flat will transact for.

**Why validate by locality?** Nearby listings share a price level. A random split lets the model peek at other homes on the same road. Holding out the whole locality, and mapping it to `other`, tests an area the model has not been shown.

**What happens in a new locality?** The name is not in the 189 kept localities, so the row uses the `other` bucket trained on rare areas. Size, bedrooms, and bathrooms still count. The result says the estimate is less reliable.

**How do you monitor and retrain?** Log locality, size, and the predicted range, without income or office location. Watch `scripts/drift_report.py`. Retrain with `scripts/retrain.py` when the listings file is updated or the logged distribution moves. Nothing here retrains on a schedule.

**How do you stop the chatbot from inventing numbers?** It receives only the analysis JSON. The system prompt says to use those numbers, to answer “I don't have that information” otherwise, and to refuse financial and legal advice. Flood and loan-advice questions are refused in code before any model is called. A session stops at 12 user questions. With no API key, ordinary questions stay off.

**What would change with real transaction data?** Train on registered prices, judge the asking price against that model, and split by time instead of only by locality. Guidance values would also fix the stamp-duty base. Rent should be observed listings, not a yield.
