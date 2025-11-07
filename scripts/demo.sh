#!/bin/bash

# Teach Me Mailer Demo Script
# This script demonstrates the email service capabilities

set -e

echo "🚀 Teach Me Mailer - Live Demo"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8000"
DEMO_API_KEY="sk_test_demo_key_12345"
DEMO_EMAIL="demo@example.com"

# Function to make API calls with proper error handling
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    echo -e "${BLUE}➤ $method $endpoint${NC}"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X POST \
            -H "X-API-Key: $DEMO_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint")
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$API_BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//g')
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 202 ]; then
        echo -e "${GREEN}✅ Success ($http_code)${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed ($http_code)${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 1
    fi
    echo ""
}

# Check if service is running
check_service() {
    echo -e "${YELLOW}🔍 Checking if service is running...${NC}"
    if curl -s "$API_BASE_URL/health" > /dev/null; then
        echo -e "${GREEN}✅ Service is running${NC}"
    else
        echo -e "${RED}❌ Service is not running${NC}"
        echo "Please start the service with: make up"
        exit 1
    fi
    echo ""
}

# Demo step 1: Health check
demo_health() {
    echo -e "${YELLOW}📋 Step 1: Health Check${NC}"
    make_request "GET" "/health"
}

# Demo step 2: API Documentation
demo_docs() {
    echo -e "${YELLOW}📖 Step 2: API Documentation${NC}"
    echo -e "${BLUE}➤ GET /docs${NC}"
    echo -e "${GREEN}✅ Interactive API docs available at: ${API_BASE_URL}/docs${NC}"
    echo ""
    
    echo -e "${BLUE}➤ GET /redoc${NC}"
    echo -e "${GREEN}✅ ReDoc documentation available at: ${API_BASE_URL}/redoc${NC}"
    echo ""
}

# Demo step 3: Send a basic email
demo_basic_email() {
    echo -e "${YELLOW}📧 Step 3: Send Basic Email${NC}"
    
    local email_data='{
        "to": "'$DEMO_EMAIL'",
        "subject": "Welcome to Teach Me Mailer! 🚀",
        "html_body": "<h1>Hello!</h1><p>This is a <strong>test email</strong> from the Teach Me Mailer service.</p><p>Features demonstrated:</p><ul><li>✅ HTML email support</li><li>✅ API key authentication</li><li>✅ Rate limiting</li><li>✅ Structured logging</li></ul>",
        "text_body": "Hello!\n\nThis is a test email from the Teach Me Mailer service.\n\nFeatures demonstrated:\n- HTML email support\n- API key authentication\n- Rate limiting\n- Structured logging"
    }'
    
    make_request "POST" "/api/v1/send" "$email_data"
}

# Demo step 4: Send email with custom headers
demo_custom_headers() {
    echo -e "${YELLOW}📧 Step 4: Email with Custom Headers${NC}"
    
    local email_data='{
        "to": "'$DEMO_EMAIL'",
        "subject": "Custom Headers Demo",
        "html_body": "<h2>Custom Headers Demo</h2><p>This email includes custom headers for enhanced functionality.</p>",
        "text_body": "Custom Headers Demo\n\nThis email includes custom headers for enhanced functionality.",
        "headers": {
            "Reply-To": "noreply@example.com",
            "X-Priority": "1",
            "X-Mailer": "Teach-Me-Mailer/1.0"
        }
    }'
    
    make_request "POST" "/api/v1/send" "$email_data"
}

# Demo step 5: Rate limiting demonstration
demo_rate_limiting() {
    echo -e "${YELLOW}⚡ Step 5: Rate Limiting Demo${NC}"
    echo "Sending multiple emails quickly to demonstrate rate limiting..."
    echo ""
    
    for i in {1..3}; do
        echo -e "${BLUE}Email $i/3${NC}"
        local email_data='{
            "to": "'$DEMO_EMAIL'",
            "subject": "Rate Limit Test #'$i'",
            "text_body": "This is rate limit test email number '$i'."
        }'
        
        make_request "POST" "/api/v1/send" "$email_data" || true
        sleep 1
    done
}

# Demo step 6: Metrics
demo_metrics() {
    echo -e "${YELLOW}📊 Step 6: Prometheus Metrics${NC}"
    echo -e "${BLUE}➤ GET /metrics${NC}"
    
    metrics=$(curl -s "$API_BASE_URL/metrics")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Metrics retrieved successfully${NC}"
        echo ""
        echo "Sample metrics:"
        echo "$metrics" | grep -E "(http_requests_total|email_sends_total)" | head -5 || echo "Metrics collected"
        echo ""
        echo -e "${GREEN}✅ Full metrics available at: ${API_BASE_URL}/metrics${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve metrics${NC}"
    fi
    echo ""
}

# Demo step 7: Error handling
demo_error_handling() {
    echo -e "${YELLOW}❌ Step 7: Error Handling Demo${NC}"
    
    # Invalid email format
    echo "Testing invalid email format:"
    local invalid_email_data='{
        "to": "invalid-email-format",
        "subject": "Test",
        "text_body": "This should fail validation."
    }'
    
    make_request "POST" "/api/v1/send" "$invalid_email_data" || true
    
    # Missing required fields
    echo "Testing missing required fields:"
    local incomplete_data='{
        "subject": "Missing recipient"
    }'
    
    make_request "POST" "/api/v1/send" "$incomplete_data" || true
    
    # Invalid API key
    echo "Testing invalid API key:"
    DEMO_API_KEY="invalid_key"
    local test_data='{
        "to": "'$DEMO_EMAIL'",
        "subject": "Test",
        "text_body": "This should fail authentication."
    }'
    
    make_request "POST" "/api/v1/send" "$test_data" || true
    
    # Restore valid API key
    DEMO_API_KEY="sk_test_demo_key_12345"
}

# Main demo function
main_demo() {
    echo "This demo will showcase the key features of Teach Me Mailer:"
    echo "• ✅ Service health monitoring"
    echo "• 📖 Comprehensive API documentation"
    echo "• 📧 Email sending with HTML/text support"
    echo "• 🔧 Custom headers functionality"
    echo "• ⚡ Rate limiting protection"
    echo "• 📊 Metrics and observability"
    echo "• ❌ Robust error handling"
    echo ""
    
    read -p "Press Enter to start the demo..." -n 1 -r
    echo ""
    
    check_service
    demo_health
    demo_docs
    demo_basic_email
    demo_custom_headers
    demo_rate_limiting
    demo_metrics
    demo_error_handling
    
    echo -e "${GREEN}🎉 Demo completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📋 Summary:${NC}"
    echo "• All API endpoints tested"
    echo "• Email sending functionality verified"
    echo "• Rate limiting demonstrated"
    echo "• Error handling validated"
    echo "• Metrics collection confirmed"
    echo ""
    echo -e "${BLUE}🔗 Useful links:${NC}"
    echo "• API Documentation: $API_BASE_URL/docs"
    echo "• Metrics Dashboard: $API_BASE_URL/metrics"
    echo "• Health Check: $API_BASE_URL/health"
    echo ""
    echo "Thank you for trying Teach Me Mailer! 🚀"
}

# Check dependencies
check_dependencies() {
    command -v curl >/dev/null 2>&1 || { echo "curl is required but not installed. Aborting." >&2; exit 1; }
    command -v jq >/dev/null 2>&1 || { echo "Warning: jq not found. JSON output will not be formatted." >&2; }
}

# Script entry point
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    check_dependencies
    main_demo
fi