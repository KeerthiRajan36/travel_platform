#!/bin/bash
set -e
cd /home/claude/travel_platform
source venv/bin/activate
rm -f travel.db

uvicorn app.main:app --host 127.0.0.1 --port 8000 > server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT

# wait for readiness
for i in $(seq 1 20); do
  if curl -s -o /dev/null http://127.0.0.1:8000/health; then break; fi
  sleep 0.5
done

BASE="http://127.0.0.1:8000"
jqget() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }

step() { echo; echo "=== $1 ==="; }

step "Register super admin"
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" -d '{
  "name":"Admin User","email":"admin@travel.com","password":"AdminPass123","role":"super_admin"}'
echo

step "Login as admin"
LOGIN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{
  "email":"admin@travel.com","password":"AdminPass123"}')
echo "$LOGIN"
TOKEN=$(echo "$LOGIN" | jqget "['access_token']")
AUTH="Authorization: Bearer $TOKEN"

step "GET /auth/me"
curl -s $BASE/auth/me -H "$AUTH"
echo

step "Create destination"
DEST=$(curl -s -X POST $BASE/destinations -H "$AUTH" -H "Content-Type: application/json" -d '{
  "name":"Manali","country":"India","state":"Himachal Pradesh","description":"Mountains","best_season":"Summer"}')
echo "$DEST"
DEST_ID=$(echo "$DEST" | jqget "['id']")

step "List destinations (search filter)"
curl -s "$BASE/destinations?search=Manali&page=1&limit=10" -H "$AUTH"
echo

step "Create tour package (start_date in future)"
START_DATE=$(python3 -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=20)).isoformat())")
END_DATE=$(python3 -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=25)).isoformat())")
PKG=$(curl -s -X POST $BASE/packages -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"package_name\":\"Manali Adventure\",\"destination_id\":$DEST_ID,\"description\":\"Fun trip\",
  \"duration_days\":5,\"base_price\":15000,\"max_capacity\":10,
  \"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\",\"status\":\"Draft\"}")
echo "$PKG"
PKG_ID=$(echo "$PKG" | jqget "['id']")

step "Publish package (PUT status=Published)"
curl -s -X PUT $BASE/packages/$PKG_ID -H "$AUTH" -H "Content-Type: application/json" -d '{"status":"Published"}'
echo

step "Test business rule: end_date before start_date should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/packages -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"package_name\":\"Bad Package\",\"destination_id\":$DEST_ID,\"duration_days\":5,\"base_price\":1000,
  \"max_capacity\":5,\"start_date\":\"2026-01-10\",\"end_date\":\"2026-01-01\"}"

step "Add itinerary day 1"
curl -s -X POST $BASE/packages/$PKG_ID/itinerary -H "$AUTH" -H "Content-Type: application/json" -d '{
  "day_number":1,"title":"Arrival","description":"Check-in","location":"Manali","start_time":"09:00:00","end_time":"12:00:00"}'
echo

step "Test business rule: day_number > duration_days should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/packages/$PKG_ID/itinerary -H "$AUTH" -H "Content-Type: application/json" -d '{
  "day_number":99,"title":"Impossible","start_time":"09:00:00","end_time":"10:00:00"}'

step "Create customer"
CUST=$(curl -s -X POST $BASE/customers -H "$AUTH" -H "Content-Type: application/json" -d '{
  "name":"Priya Sharma","email":"priya@example.com","phone":"9999999999","address":"Chennai"}')
echo "$CUST"
CUST_ID=$(echo "$CUST" | jqget "['id']")

step "Create booking (2 travelers)"
BOOKING=$(curl -s -X POST $BASE/bookings -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"customer_id\":$CUST_ID,\"package_id\":$PKG_ID,\"number_of_travelers\":2,\"discount\":500,\"tax\":300}")
echo "$BOOKING"
BOOKING_ID=$(echo "$BOOKING" | jqget "['id']")
TOTAL_AMOUNT=$(echo "$BOOKING" | jqget "['total_amount']")
echo "TOTAL_AMOUNT=$TOTAL_AMOUNT"

step "Test business rule: duplicate active booking for same customer+package should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/bookings -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"customer_id\":$CUST_ID,\"package_id\":$PKG_ID,\"number_of_travelers\":1}"

step "Test business rule: overbooking should fail (11 > available slots)"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/bookings -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"customer_id\":$CUST_ID,\"package_id\":$PKG_ID,\"number_of_travelers\":11}"

step "Add travelers to booking"
curl -s -X POST $BASE/bookings/$BOOKING_ID/travelers -H "$AUTH" -H "Content-Type: application/json" -d '{
  "full_name":"Priya Sharma","date_of_birth":"1990-05-01","gender":"female","passport_number":"P1234567","nationality":"Indian"}'
echo
curl -s -X POST $BASE/bookings/$BOOKING_ID/travelers -H "$AUTH" -H "Content-Type: application/json" -d '{
  "full_name":"Raj Sharma","date_of_birth":"1988-03-15","gender":"male","passport_number":"P7654321","nationality":"Indian"}'
echo

step "Pay full amount -> should auto-confirm booking"
PAY=$(curl -s -X POST $BASE/payments/$BOOKING_ID -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"amount\":$TOTAL_AMOUNT,\"payment_method\":\"UPI\",\"transaction_id\":\"TXN-0001\"}")
echo "$PAY"

step "Verify booking is now Confirmed and slots reduced"
curl -s $BASE/bookings/$BOOKING_ID -H "$AUTH"
echo
curl -s $BASE/packages/$PKG_ID -H "$AUTH"
echo

step "Test business rule: duplicate transaction_id should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/payments/$BOOKING_ID -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"amount\":100,\"payment_method\":\"UPI\",\"transaction_id\":\"TXN-0001\"}"

step "Create hotel + room + reservation"
HOTEL=$(curl -s -X POST $BASE/hotels -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"hotel_name\":\"Snow View Resort\",\"destination_id\":$DEST_ID,\"rating\":4}")
echo "$HOTEL"
HOTEL_ID=$(echo "$HOTEL" | jqget "['id']")
ROOM=$(curl -s -X POST $BASE/rooms -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"hotel_id\":$HOTEL_ID,\"room_type\":\"Deluxe\",\"room_number\":\"101\",\"price_per_night\":2000,\"capacity\":2}")
echo "$ROOM"
ROOM_ID=$(echo "$ROOM" | jqget "['id']")
RES=$(curl -s -X POST $BASE/hotel-reservations -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"booking_id\":$BOOKING_ID,\"room_id\":$ROOM_ID,\"check_in\":\"$START_DATE\",\"check_out\":\"$END_DATE\",\"number_of_rooms\":1}")
echo "$RES"

step "Test business rule: overlapping reservation should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/hotel-reservations -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"booking_id\":$BOOKING_ID,\"room_id\":$ROOM_ID,\"check_in\":\"$START_DATE\",\"check_out\":\"$END_DATE\",\"number_of_rooms\":1}"

step "Create guide + assign to package"
GUIDE=$(curl -s -X POST $BASE/guides -H "$AUTH" -H "Content-Type: application/json" -d '{
  "name":"Amit Guide","email":"amit@guides.com","phone":"8888888888","specialization":"Trekking"}')
echo "$GUIDE"
GUIDE_ID=$(echo "$GUIDE" | jqget "['id']")
curl -s -X POST $BASE/packages/$PKG_ID/assign-guide/$GUIDE_ID -H "$AUTH"
echo

step "Test business rule: overlapping guide assignment should fail (create 2nd package same dates)"
PKG2=$(curl -s -X POST $BASE/packages -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"package_name\":\"Manali Adventure 2\",\"destination_id\":$DEST_ID,\"duration_days\":5,\"base_price\":15000,
  \"max_capacity\":10,\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\",\"status\":\"Published\"}")
PKG2_ID=$(echo "$PKG2" | jqget "['id']")
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/packages/$PKG2_ID/assign-guide/$GUIDE_ID -H "$AUTH"

step "Dashboard summary"
curl -s $BASE/dashboard/summary -H "$AUTH"
echo

step "Cancel booking via refund engine (should give 90% refund, >15 days out)"
CANCEL=$(curl -s -X POST $BASE/bookings/$BOOKING_ID/cancel -H "$AUTH" -H "Content-Type: application/json" -d '{"reason":"change of plans"}')
echo "$CANCEL"

step "Verify package slots restored after cancellation"
curl -s $BASE/packages/$PKG_ID -H "$AUTH"
echo

step "Mark booking Completed directly in DB to test review flow"
python3 -c "
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus
db = SessionLocal()
b = db.query(Booking).filter(Booking.id == $BOOKING_ID).first()
b.booking_status = BookingStatus.COMPLETED
db.commit()
print('booking status set to', b.booking_status)
db.close()
"

step "Create review for completed booking"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST "$BASE/reviews?customer_id=$CUST_ID" -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"booking_id\":$BOOKING_ID,\"rating\":5,\"review_text\":\"Amazing trip!\"}"

step "Test business rule: duplicate review for same booking should fail"
curl -s -w "\nSTATUS:%{http_code}\n" -X POST "$BASE/reviews?customer_id=$CUST_ID" -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"booking_id\":$BOOKING_ID,\"rating\":4}"

step "List package reviews"
curl -s $BASE/packages/$PKG_ID/reviews -H "$AUTH"
echo

step "Test RBAC: customer role should be forbidden from creating a destination"
CUST_LOGIN=$(curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" -d '{
  "name":"Regular Customer","email":"cust_user@example.com","password":"CustPass123","role":"customer"}')
echo "$CUST_LOGIN"
CTOKEN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{
  "email":"cust_user@example.com","password":"CustPass123"}' | jqget "['access_token']")
curl -s -w "\nSTATUS:%{http_code}\n" -X POST $BASE/destinations -H "Authorization: Bearer $CTOKEN" -H "Content-Type: application/json" -d '{
  "name":"Goa","country":"India"}'

step "Test auth: no token should be unauthorized"
curl -s -w "\nSTATUS:%{http_code}\n" $BASE/dashboard/summary

step "Rate limit config check (not exhausting limit, just confirming middleware doesn't break normal traffic)"
curl -s -w "\nSTATUS:%{http_code}\n" $BASE/health

echo
echo "=== SMOKE TEST COMPLETE ==="
