package serpapi

import (
	"github.com/gosom/google-maps-scraper/gmaps"
)

// ToEntry converts a SerpApi SearchResult to gmaps.Entry format
func (sr *SearchResult) ToEntry(jobID string) *gmaps.Entry {
	entry := &gmaps.Entry{
		ID:           jobID,
		Title:        sr.Title,
		PlaceID:      sr.PlaceID,
		DataID:       sr.DataID,
		Address:      sr.Address,
		Latitude:     sr.Latitude,
		Longtitude:   sr.Longitude,
		ReviewRating: sr.Rating,
		ReviewCount:  sr.Reviews,
		Category:     sr.Type,
		Phone:        sr.Phone,
		WebSite:      sr.Website,
		PlusCode:     sr.PlusCode,
		Thumbnail:    sr.Thumbnail,
	}

	// Set categories if type is available
	if sr.Type != "" {
		entry.Categories = []string{sr.Type}
	}

	// Initialize empty maps to avoid nil pointer issues
	if entry.OpenHours == nil {
		entry.OpenHours = make(map[string][]string)
	}

	if entry.PopularTimes == nil {
		entry.PopularTimes = make(map[string]map[int]int)
	}

	if entry.ReviewsPerRating == nil {
		entry.ReviewsPerRating = make(map[int]int)
	}

	// Parse hours if available
	if sr.Hours != "" {
		// SerpApi returns hours as a single string, we'll store it under "General"
		entry.OpenHours["General"] = []string{sr.Hours}
	}

	return entry
}

// ToEntries converts multiple SerpApi SearchResults to gmaps.Entry slice
func ToEntries(results []SearchResult, jobID string) []*gmaps.Entry {
	entries := make([]*gmaps.Entry, 0, len(results))

	for i := range results {
		entry := results[i].ToEntry(jobID)
		entries = append(entries, entry)
	}

	return entries
}
