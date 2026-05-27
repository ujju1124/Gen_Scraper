package serpapi

import (
	"context"
	"fmt"
	"strconv"

	g "github.com/serpapi/google-search-results-golang"
)

// Client wraps SerpApi functionality
type Client struct {
	apiKey string
}

// NewClient creates a new SerpApi client
func NewClient(apiKey string) *Client {
	return &Client{
		apiKey: apiKey,
	}
}

// SearchResult represents a single place from SerpApi
type SearchResult struct {
	Title           string  `json:"title"`
	PlaceID         string  `json:"place_id"`
	DataID          string  `json:"data_id"`
	Address         string  `json:"address"`
	Latitude        float64 `json:"latitude"`
	Longitude       float64 `json:"longitude"`
	Rating          float64 `json:"rating"`
	Reviews         int     `json:"reviews"`
	Type            string  `json:"type"`
	Phone           string  `json:"phone"`
	Website         string  `json:"website"`
	Hours           string  `json:"hours"`
	PlusCode        string  `json:"plus_code"`
	Thumbnail       string  `json:"thumbnail"`
	ServiceOptions  map[string]bool `json:"service_options"`
}

// SearchParams represents search parameters
type SearchParams struct {
	Query          string
	Location       string
	GeoCoordinates string
	Language       string
	MaxResults     int
	Zoom           int
}

// Search performs a Google Maps search using SerpApi
func (c *Client) Search(ctx context.Context, params SearchParams) ([]SearchResult, error) {
	// Build SerpApi parameters
	parameter := map[string]string{
		"engine":  "google_maps",
		"q":       params.Query,
		"api_key": c.apiKey,
	}

	// Add optional parameters
	if params.Language != "" {
		parameter["hl"] = params.Language
	}

	if params.GeoCoordinates != "" {
		// SerpApi expects coordinates in @lat,lon,zoom format for Google Maps
		// Example: @40.7455096,-74.0083012,15.1z
		zoom := params.Zoom
		if zoom == 0 {
			zoom = 14 // Default zoom
		}
		parameter["ll"] = fmt.Sprintf("@%s,%dz", params.GeoCoordinates, zoom)
	} else if params.Location != "" {
		parameter["location"] = params.Location
	}

	// Set type to search (not place details)
	parameter["type"] = "search"

	// Create search
	search := g.NewGoogleSearch(parameter, c.apiKey)
	results, err := search.GetJSON()
	if err != nil {
		return nil, fmt.Errorf("serpapi search failed: %w", err)
	}

	// Parse results
	return c.parseResults(results)
}

// parseResults converts SerpApi response to our format
func (c *Client) parseResults(data map[string]interface{}) ([]SearchResult, error) {
	var results []SearchResult

	// Get local_results array
	localResults, ok := data["local_results"].([]interface{})
	if !ok {
		return results, nil // No results found
	}

	for _, item := range localResults {
		place, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		result := SearchResult{}

		// Extract basic info
		if title, ok := place["title"].(string); ok {
			result.Title = title
		}
		if placeID, ok := place["place_id"].(string); ok {
			result.PlaceID = placeID
		}
		if dataID, ok := place["data_id"].(string); ok {
			result.DataID = dataID
		}
		if address, ok := place["address"].(string); ok {
			result.Address = address
		}
		if placeType, ok := place["type"].(string); ok {
			result.Type = placeType
		}
		if phone, ok := place["phone"].(string); ok {
			result.Phone = phone
		}
		if website, ok := place["website"].(string); ok {
			result.Website = website
		}
		if hours, ok := place["hours"].(string); ok {
			result.Hours = hours
		}
		if thumbnail, ok := place["thumbnail"].(string); ok {
			result.Thumbnail = thumbnail
		}

		// Extract GPS coordinates
		if gps, ok := place["gps_coordinates"].(map[string]interface{}); ok {
			if lat, ok := gps["latitude"].(float64); ok {
				result.Latitude = lat
			}
			if lon, ok := gps["longitude"].(float64); ok {
				result.Longitude = lon
			}
		}

		// Extract rating
		if rating, ok := place["rating"].(float64); ok {
			result.Rating = rating
		}

		// Extract reviews count
		if reviews, ok := place["reviews"].(float64); ok {
			result.Reviews = int(reviews)
		} else if reviewsStr, ok := place["reviews"].(string); ok {
			if reviewsInt, err := strconv.Atoi(reviewsStr); err == nil {
				result.Reviews = reviewsInt
			}
		}

		// Extract plus code
		if plusCode, ok := place["plus_code"].(string); ok {
			result.PlusCode = plusCode
		}

		// Extract service options
		if serviceOpts, ok := place["service_options"].(map[string]interface{}); ok {
			result.ServiceOptions = make(map[string]bool)
			for key, val := range serviceOpts {
				if boolVal, ok := val.(bool); ok {
					result.ServiceOptions[key] = boolVal
				}
			}
		}

		results = append(results, result)
	}

	return results, nil
}

// GetPlaceDetails gets detailed information about a specific place
func (c *Client) GetPlaceDetails(ctx context.Context, dataID string) (map[string]interface{}, error) {
	parameter := map[string]string{
		"engine":  "google_maps",
		"type":    "place",
		"data_id": dataID,
		"api_key": c.apiKey,
	}

	search := g.NewGoogleSearch(parameter, c.apiKey)
	results, err := search.GetJSON()
	if err != nil {
		return nil, fmt.Errorf("serpapi place details failed: %w", err)
	}

	return results, nil
}
