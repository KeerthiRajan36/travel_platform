#!/bin/bash
set -e
cd /home/claude/travel_platform
. venv/bin/activate
rm -f travel.db server_bonus.log

uvicorn app.main:app --host 127.0.0.1 --port 8001 > server_bonus.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT
for i in $(seq 1 20); do curl -s -o /dev/null http://127.0.0.1:8001/health && break; sleep 0.5; done

BASE="http://127.0.0.1:8001"
jqget() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }
step() { echo; echo "=== $1 ==="; }

step "Versioned health check still unversioned"
curl -s -w "\nSTATUS:%{http_code}\n" $BASE/health

step "Register + login (legacy unversioned path)"
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" -d '{
  "name":"Admin","email":"admin@bonus.com","password":"AdminPass123","role":"super_admin"}' > /dev/null
TOKEN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{
  "email":"admin@bonus.com","password":"AdminPass123"}' | jqget "['access_token']")
AUTH="Authorization: Bearer $TOKEN"

step "Same endpoint also reachable under versioned /api/v1 prefix"
curl -s -w "\nSTATUS:%{http_code}\n" $BASE/api/v1/auth/me -H "$AUTH"

step "Set up a fully paid, confirmed booking"
DEST=$(curl -s -X POST $BASE/destinations -H "$AUTH" -H "Content-Type: application/json" -d '{"name":"Goa","country":"India"}')
DEST_ID=$(echo "$DEST" | jqget "['id']")
START_DATE=$(python3 -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=10)).isoformat())")
END_DATE=$(python3 -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=15)).isoformat())")
PKG=$(curl -s -X POST $BASE/packages -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"package_name\":\"Goa Getaway\",\"destination_id\":$DEST_ID,\"duration_days\":5,\"base_price\":8000,
  \"max_capacity\":10,\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\",\"status\":\"Published\"}")
PKG_ID=$(echo "$PKG" | jqget "['id']")
CUST=$(curl -s -X POST $BASE/customers -H "$AUTH" -H "Content-Type: application/json" -d '{
  "name":"Bonus Tester","email":"bonus_tester@example.com","phone":"9998887777"}')
CUST_ID=$(echo "$CUST" | jqget "['id']")
BOOKING=$(curl -s -X POST $BASE/bookings -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"customer_id\":$CUST_ID,\"package_id\":$PKG_ID,\"number_of_travelers\":2}")
BOOKING_ID=$(echo "$BOOKING" | jqget "['id']")
TOTAL=$(echo "$BOOKING" | jqget "['total_amount']")

step "Open a WebSocket listener BEFORE paying, then trigger payment, and confirm we receive the live status push"
python3 - "$BOOKING_ID" "$TOTAL" "$TOKEN" << 'PYEOF'
import asyncio, sys, json
import httpx
import websockets

booking_id, total, token = sys.argv[1], sys.argv[2], sys.argv[3]

async def main():
    uri = f"ws://127.0.0.1:8001/ws/bookings/{booking_id}"
    async with websockets.connect(uri) as ws:
        initial = json.loads(await ws.recv())
        print("WS initial message:", initial)
        assert initial["status"] == "Pending", f"expected Pending, got {initial}"

        # Trigger the payment via a normal HTTP call while the socket is open.
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://127.0.0.1:8001/payments/{booking_id}",
                json={"amount": float(total), "payment_method": "UPI", "transaction_id": "TXN-WS-1"},
                headers={"Authorization": f"Bearer {token}"},
            )
            print("Payment HTTP status:", resp.status_code)

        update = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print("WS pushed update:", update)
        assert update["status"] == "Confirmed", f"expected Confirmed, got {update}"
        print("WEBSOCKET LIVE STATUS TEST: PASSED")

asyncio.run(main())
PYEOF

step "Dashboard summary (first call = cache miss)"
curl -s $BASE/dashboard/summary -H "$AUTH"
echo
step "Dashboard summary again (second call = cache hit, same numbers)"
curl -s $BASE/dashboard/summary -H "$AUTH"
echo

step "Download booking confirmation PDF"
curl -s -o /tmp/booking_confirmation.pdf -w "STATUS:%{http_code}\n" $BASE/bookings/$BOOKING_ID/confirmation-pdf -H "$AUTH"
file /tmp/booking_confirmation.pdf
ls -la /tmp/booking_confirmation.pdf

step "Download booking QR code"
curl -s -o /tmp/booking_qr.png -w "STATUS:%{http_code}\n" $BASE/bookings/$BOOKING_ID/qr-code -H "$AUTH"
file /tmp/booking_qr.png

step "Export operations report as Excel"
curl -s -o /tmp/operations_report.xlsx -w "STATUS:%{http_code}\n" $BASE/dashboard/reports/export -H "$AUTH"
file /tmp/operations_report.xlsx
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('/tmp/operations_report.xlsx')
print('Sheets:', wb.sheetnames)
ws = wb['Summary']
for row in ws.iter_rows(values_only=True):
    print(row)
"

echo
echo "=== BONUS FEATURES SMOKE TEST COMPLETE ==="
