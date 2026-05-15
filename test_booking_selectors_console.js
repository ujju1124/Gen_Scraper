/**
 * Booking.com Detail Page Selector Testing Script
 * 
 * INSTRUCTIONS:
 * 1. Open any Booking.com hotel detail page (e.g., https://www.booking.com/hotel/np/...)
 * 2. Open browser DevTools (F12)
 * 3. Go to Console tab
 * 4. Copy and paste this ENTIRE script
 * 5. Press Enter
 * 6. Copy the output and send it back
 */

console.clear();
console.log("=".repeat(80));
console.log("BOOKING.COM DETAIL PAGE SELECTOR TEST");
console.log("=".repeat(80));
console.log("");

// Test results object
const results = {
    url: window.location.href,
    hotelName: document.title,
    timestamp: new Date().toISOString(),
    tests: {}
};

// Helper function to test a selector
function testSelector(name, selector, description) {
    console.log(`\n📋 Testing: ${name}`);
    console.log(`   Selector: ${selector}`);
    console.log(`   Purpose: ${description}`);
    
    try {
        const elements = document.querySelectorAll(selector);
        const count = elements.length;
        
        if (count === 0) {
            console.log(`   ❌ NOT FOUND (0 elements)`);
            results.tests[name] = {
                selector: selector,
                found: false,
                count: 0,
                samples: []
            };
        } else {
            console.log(`   ✅ FOUND (${count} elements)`);
            
            // Get sample text from first 3 elements
            const samples = [];
            for (let i = 0; i < Math.min(3, count); i++) {
                const text = elements[i].textContent.trim().substring(0, 100);
                if (text) {
                    samples.push(text);
                    console.log(`   Sample ${i + 1}: "${text}"`);
                }
            }
            
            results.tests[name] = {
                selector: selector,
                found: true,
                count: count,
                samples: samples
            };
        }
    } catch (error) {
        console.log(`   ⚠️  ERROR: ${error.message}`);
        results.tests[name] = {
            selector: selector,
            found: false,
            error: error.message
        };
    }
}

// Test all our current selectors
console.log("\n" + "=".repeat(80));
console.log("TESTING CURRENT SELECTORS FROM DATABASE");
console.log("=".repeat(80));

testSelector(
    "detail_checkin",
    "DIV.b99b6ef58f",
    "Check-in time"
);

testSelector(
    "detail_checkout",
    "DIV.b99b6ef58f",
    "Check-out time (same selector as check-in)"
);

testSelector(
    "detail_description",
    "P.b99b6ef58f.f1152bae71",
    "Full description text"
);

testSelector(
    "detail_languages",
    "SPAN.f6b6d2a959",
    "Languages spoken"
);

testSelector(
    "detail_amenities",
    'span[data-testid="facility-name"], .e50d7535fa',
    "Amenities/facilities list"
);

testSelector(
    "detail_rating",
    "div.a9918d47bf",
    "Rating score"
);

// Test alternative selectors that might work better
console.log("\n" + "=".repeat(80));
console.log("TESTING ALTERNATIVE SELECTORS (More Stable)");
console.log("=".repeat(80));

testSelector(
    "alt_amenities_1",
    '[data-testid="property-most-popular-facilities-wrapper"] span',
    "Amenities via data-testid wrapper"
);

testSelector(
    "alt_amenities_2",
    '[data-capla-component="b-property-web-property-page/PropertyFacilitiesBlock"] li',
    "Amenities via facilities block"
);

testSelector(
    "alt_checkin_1",
    '[data-testid="check-in-time"]',
    "Check-in via data-testid"
);

testSelector(
    "alt_checkout_1",
    '[data-testid="check-out-time"]',
    "Check-out via data-testid"
);

testSelector(
    "alt_description_1",
    '[data-capla-component="b-property-web-property-page/PropertyDescriptionBlock"] p',
    "Description via component"
);

testSelector(
    "alt_description_2",
    '#property_description_content',
    "Description via ID"
);

testSelector(
    "alt_languages_1",
    '[data-testid="languages-spoken"] span',
    "Languages via data-testid"
);

// Test JSON-LD extraction (this is what's working)
console.log("\n" + "=".repeat(80));
console.log("TESTING JSON-LD STRUCTURED DATA (Currently Working)");
console.log("=".repeat(80));

try {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    console.log(`\n📋 Found ${scripts.length} JSON-LD script tags`);
    
    let hotelData = null;
    for (const script of scripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data["@type"] === "Hotel" || data["@type"] === "LodgingBusiness") {
                hotelData = data;
                console.log(`   ✅ Found Hotel/LodgingBusiness schema`);
                console.log(`   Name: ${data.name || 'N/A'}`);
                console.log(`   Rating: ${data.aggregateRating?.ratingValue || 'N/A'}`);
                console.log(`   Reviews: ${data.aggregateRating?.reviewCount || 'N/A'}`);
                console.log(`   Address: ${data.address?.streetAddress || 'N/A'}`);
                console.log(`   Description: ${(data.description || '').substring(0, 100)}...`);
                break;
            }
        } catch (e) {
            // Skip invalid JSON
        }
    }
    
    results.jsonld = {
        found: hotelData !== null,
        data: hotelData
    };
    
    if (!hotelData) {
        console.log(`   ❌ No Hotel schema found in JSON-LD`);
    }
} catch (error) {
    console.log(`   ⚠️  ERROR: ${error.message}`);
    results.jsonld = { found: false, error: error.message };
}

// Discover what's actually on the page
console.log("\n" + "=".repeat(80));
console.log("PAGE STRUCTURE DISCOVERY");
console.log("=".repeat(80));

// Find sections with "facilities" or "amenities"
console.log("\n📋 Searching for Facilities/Amenities sections:");
const facilitiesKeywords = ['facilities', 'amenities', 'features'];
facilitiesKeywords.forEach(keyword => {
    const elements = document.querySelectorAll(`[class*="${keyword}"], [id*="${keyword}"], [data-testid*="${keyword}"]`);
    if (elements.length > 0) {
        console.log(`   ✅ Found ${elements.length} elements with "${keyword}"`);
        elements.forEach((el, i) => {
            if (i < 3) {
                console.log(`      - ${el.tagName}.${el.className.substring(0, 50)} [${el.id}]`);
            }
        });
    }
});

// Find sections with "check-in" or "check-out"
console.log("\n📋 Searching for Check-in/Check-out sections:");
const checkinKeywords = ['check-in', 'check-out', 'checkin', 'checkout'];
checkinKeywords.forEach(keyword => {
    const elements = document.querySelectorAll(`[class*="${keyword}"], [id*="${keyword}"], [data-testid*="${keyword}"]`);
    if (elements.length > 0) {
        console.log(`   ✅ Found ${elements.length} elements with "${keyword}"`);
        elements.forEach((el, i) => {
            if (i < 3) {
                const text = el.textContent.trim().substring(0, 80);
                console.log(`      - ${el.tagName}.${el.className.substring(0, 30)}: "${text}"`);
            }
        });
    }
});

// Find sections with "description"
console.log("\n📋 Searching for Description sections:");
const descKeywords = ['description', 'about'];
descKeywords.forEach(keyword => {
    const elements = document.querySelectorAll(`[class*="${keyword}"], [id*="${keyword}"], [data-testid*="${keyword}"]`);
    if (elements.length > 0) {
        console.log(`   ✅ Found ${elements.length} elements with "${keyword}"`);
        elements.forEach((el, i) => {
            if (i < 2) {
                console.log(`      - ${el.tagName}.${el.className.substring(0, 50)} [${el.id}]`);
            }
        });
    }
});

// Find all data-testid attributes (most stable selectors)
console.log("\n📋 All data-testid attributes on page (first 20):");
const testIds = new Set();
document.querySelectorAll('[data-testid]').forEach(el => {
    testIds.add(el.getAttribute('data-testid'));
});
const testIdArray = Array.from(testIds).slice(0, 20);
testIdArray.forEach(id => {
    console.log(`   - [data-testid="${id}"]`);
});
results.availableTestIds = testIdArray;

// Summary
console.log("\n" + "=".repeat(80));
console.log("SUMMARY");
console.log("=".repeat(80));

const currentSelectors = Object.keys(results.tests).filter(k => k.startsWith('detail_'));
const workingCurrent = currentSelectors.filter(k => results.tests[k].found).length;
const altSelectors = Object.keys(results.tests).filter(k => k.startsWith('alt_'));
const workingAlt = altSelectors.filter(k => results.tests[k].found).length;

console.log(`\n📊 Current Selectors: ${workingCurrent}/${currentSelectors.length} working`);
console.log(`📊 Alternative Selectors: ${workingAlt}/${altSelectors.length} working`);
console.log(`📊 JSON-LD: ${results.jsonld?.found ? '✅ Working' : '❌ Not found'}`);

console.log("\n" + "=".repeat(80));
console.log("COPY THE JSON BELOW AND SEND IT BACK");
console.log("=".repeat(80));
console.log("\n");

// Output results as JSON
console.log(JSON.stringify(results, null, 2));

console.log("\n" + "=".repeat(80));
console.log("TEST COMPLETE");
console.log("=".repeat(80));
console.log("\n💡 TIP: If you see errors, try scrolling down the page to load all content,");
console.log("   then run this script again.");
console.log("\n");
