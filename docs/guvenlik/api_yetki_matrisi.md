# API yetki matrisi

Kaynak koddan üretilir (`python -m app.access_matrix`); elle düzenlemeyin.
Roller: Y yönetici, D depo, Ü üretim, K kalite, M mağaza, S satış (telefon). "Giriş" = oturum açmış herkes.

Doğrulama: `tests/test_access_matrix.py` her uca girişsiz istek atar (401 beklenir) ve izinli olmayan her rolle istek atar (403 beklenir).

| Yöntem | Yol | Kimlik | İzinli roller |
|---|---|---|---|
| GET | `/api/v1/adjustments` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/adjustments` | gerekli | Y, D |
| POST | `/api/v1/ai/cutting-forecast` | gerekli | Y, Ü |
| GET | `/api/v1/ai/evaluation` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/ai/production-forecast` | gerekli | Y, Ü |
| GET | `/api/v1/alerts` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/alerts/ack-all` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/alerts/run-rules` | gerekli | Y |
| GET | `/api/v1/alerts/subscriptions` | gerekli | Y, D, Ü, K, M |
| PUT | `/api/v1/alerts/subscriptions` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/alerts/summary` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/alerts/{alert_id}/ack` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/audit` | gerekli | Y |
| GET | `/api/v1/audit/export.csv` | gerekli | Y |
| POST | `/api/v1/auth/change-password` | gerekli | giriş |
| POST | `/api/v1/auth/login` | — | herkese açık |
| POST | `/api/v1/auth/logout` | gerekli | giriş |
| GET | `/api/v1/auth/me` | gerekli | giriş |
| POST | `/api/v1/calc/cutting` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/calc/ekp` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/cutting-recipes` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/cutting-recipes` | gerekli | Y, Ü |
| GET | `/api/v1/cutting-recipes/{recipe_id}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/cuttings` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/cuttings` | gerekli | Y, Ü |
| GET | `/api/v1/cuttings/{cutting_id}` | gerekli | Y, D, Ü, K, M |
| PUT | `/api/v1/cuttings/{cutting_id}` | gerekli | Y, Ü |
| POST | `/api/v1/cuttings/{cutting_id}/approve` | gerekli | Y, Ü |
| POST | `/api/v1/cuttings/{cutting_id}/preview` | gerekli | Y, Ü |
| GET | `/api/v1/dashboard` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/dashboard/charts` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/day-end` | gerekli | Y, M |
| GET | `/api/v1/health` | — | herkese açık |
| GET | `/api/v1/lots` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/lots/{lot_no}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/lots/{lot_no}/movements` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/mail` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/mail/batch` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/mail/deliver` | gerekli | Y |
| GET | `/api/v1/mail/outbox` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/mail/recipients` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/mail/status` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/mail/{message_id}/retry` | gerekli | Y |
| POST | `/api/v1/movements/{movement_id}/reverse` | gerekli | Y, D |
| GET | `/api/v1/partners` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/partners` | gerekli | Y, D, M |
| PUT | `/api/v1/partners/{partner_id}` | gerekli | Y, D, M |
| GET | `/api/v1/production-orders` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/production-orders` | gerekli | Y, Ü |
| GET | `/api/v1/production-orders/{order_id}` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/production-orders/{order_id}/cancel` | gerekli | Y, Ü |
| POST | `/api/v1/production-orders/{order_id}/complete` | gerekli | Y, Ü |
| POST | `/api/v1/production-orders/{order_id}/ship` | gerekli | Y, Ü |
| GET | `/api/v1/products` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/products` | gerekli | Y |
| PUT | `/api/v1/products/{product_id}` | gerekli | Y |
| GET | `/api/v1/purchases` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/purchases` | gerekli | Y, D |
| POST | `/api/v1/purchases/parse-text` | gerekli | Y, D |
| GET | `/api/v1/purchases/{purchase_id}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/recalls` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/recalls` | gerekli | Y, K |
| GET | `/api/v1/recalls/{recall_id}` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/recalls/{recall_id}/close` | gerekli | Y, K |
| GET | `/api/v1/recalls/{recall_id}/export.csv` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/reports` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/reports/{code}` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/reports/{code}/email` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/reprocessing` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/reprocessing` | gerekli | Y, Ü |
| GET | `/api/v1/returns` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/returns` | gerekli | Y, K, M |
| GET | `/api/v1/sale-lines/{sale_line_id}/onward-deliveries` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/sale-lines/{sale_line_id}/onward-deliveries` | gerekli | Y, K, M |
| GET | `/api/v1/sales` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/sales` | gerekli | Y, M |
| GET | `/api/v1/sales/{sale_id}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/settings/alarm-thresholds` | gerekli | Y, D, Ü, K, M |
| PUT | `/api/v1/settings/alarm-thresholds` | gerekli | Y |
| GET | `/api/v1/stock` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/stock-counts` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/stock-counts` | gerekli | Y, D, S |
| GET | `/api/v1/stock-counts/{count_id}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/sync/day-end` | gerekli | S |
| GET | `/api/v1/sync/pull` | gerekli | S |
| POST | `/api/v1/sync/push` | gerekli | S |
| GET | `/api/v1/trace/backward/{lot_no}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/trace/forward/{lot_no}` | gerekli | Y, D, Ü, K, M |
| GET | `/api/v1/transfers` | gerekli | Y, D, Ü, K, M |
| POST | `/api/v1/transfers` | gerekli | Y, D |
| GET | `/api/v1/users` | gerekli | Y |
| POST | `/api/v1/users` | gerekli | Y |
| PUT | `/api/v1/users/{user_id}` | gerekli | Y |
| POST | `/api/v1/users/{user_id}/reset-password` | gerekli | Y |
| GET | `/api/v1/warehouses` | gerekli | Y, D, Ü, K, M |

Toplam 95 uç; herkese açık: 2.
