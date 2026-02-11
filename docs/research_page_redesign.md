# Research Page Redesign - Design Document

> **Status**: Complete
> **Author**: Claude Code
> **Date**: 2026-02-11
> **Reference**: Claude.ai main page UI pattern

---

## 1. Overview

### 1.1 Objective
Refactor the Research page from a complex two-column layout to a minimal, search-centric design inspired by Claude's main interface. The goal is to simplify the user experience while maintaining all essential functionality.

### 1.2 Current State
```
┌─────────────────────────────────────────────────────────────────────┐
│  Research                                    user_id [default] [↻] │
│  Tracks, memory inbox, and personalized paper recommendations      │
├─────────────────────────────┬───────────────────────────────────────┤
│  Tracks            [New]    │  Context Builder                      │
│  ┌─────────────────────┐    │  ┌─────────────────────────────────┐  │
│  │ RAG [Active] [Re-]  │    │  │ Query: [e.g. reranking for RAG] │  │
│  │ boyu       [Activate]│    │  │ Stage: [Auto ▼]  Exploration: []│  │
│  │ test       [Activate]│    │  │ Diversity: []                   │  │
│  │ CV         [Activate]│    │  │        [Build Context]          │  │
│  └─────────────────────┘    │  └─────────────────────────────────┘  │
│  [Clear Track Memory]       │                                       │
│                             │  [Recommendations] [Memory] [Evals]   │
│                             │  ┌─────────────────────────────────┐  │
│                             │  │ Paper Recommendations            │  │
│                             │  │ (Build context to fetch...)     │  │
│                             │  └─────────────────────────────────┘  │
└─────────────────────────────┴───────────────────────────────────────┘
```

### 1.3 Target State (Claude-inspired)
```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                                                                     │
│                                                                     │
│                     📚 What papers are you looking for?             │
│                                                                     │
│            ┌────────────────────────────────────────────┐           │
│            │ Search for papers...                       │           │
│            │                                            │           │
│            │                             [RAG ▼] [🔍]   │           │
│            └────────────────────────────────────────────┘           │
│                                                                     │
│          [🔬 ML Security] [🤖 LLM] [📊 RAG] [+ New Track]          │
│                                                                     │
│                                                                     │
│                    (Search results appear here)                     │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Design Specifications

### 2.1 Page Layout

| Aspect | Specification |
|--------|---------------|
| **Layout** | Single-column, vertically centered |
| **Max Width** | 720px for search box, 1200px for results |
| **Background** | Subtle warm gray (`bg-stone-50` or `#faf9f7`) |
| **Initial State** | Search box centered vertically |
| **After Search** | Search box moves to top, results below |

### 2.2 Header Section

**Greeting Banner** (Optional, Claude-style):
- Time-based greeting: "Good morning/afternoon/evening"
- Or static: "What papers are you looking for?"
- Typography: Large, serif or semi-bold sans-serif
- Optional icon: 📚 or custom research icon

### 2.3 Search Box Component

```
┌──────────────────────────────────────────────────────────────────┐
│  Search for papers on RAG, transformers, security...             │
│                                                                  │
│                                            ┌─────────┐ ┌──┐      │
│                                            │ RAG  ▼  │ │🔍│      │
│                                            └─────────┘ └──┘      │
└──────────────────────────────────────────────────────────────────┘
```

| Element | Description | Position |
|---------|-------------|----------|
| **Search Input** | Multi-line textarea, auto-expand | Full width |
| **Placeholder** | "Search for papers on RAG, transformers, security..." | — |
| **Track Selector** | Dropdown showing active track | Bottom-right |
| **Search Button** | Icon button or Enter to submit | Bottom-right |

> **Note**: The [+] button was removed from initial implementation to keep the interface clean. It may be added in a future iteration for attaching files or adding context.

### 2.4 Track Selector (Replaces Tracks Box)

**Dropdown Design**:
```
┌─────────────────────┐
│  RAG            ▼   │  ← Current active track
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ ✓ RAG               │  ← Active (checkmark)
│   boyu              │
│   test              │
│   CV                │
├─────────────────────┤
│ + New Track         │  ← Create new
│ ⚙ Manage Tracks     │  ← Opens modal
└─────────────────────┘
```

**Interactions**:
- Click dropdown → Show track list
- Select track → Activate track, close dropdown
- "+ New Track" → Open create track modal
- "⚙ Manage Tracks" → Open management modal (Edit, Clear Memory)

**Manage Tracks Modal**:
```
┌─────────────────────────────────────────────┐
│  Manage Tracks                          ✕   │
│  View and manage your research tracks.      │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐    │
│  │ CV           [Active]    [Edit] [🗑] │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │ boyu                     [Edit] [🗑] │    │
│  │ test description...                 │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

- **Edit button**: Opens EditTrackModal to modify name, description, keywords
- **Delete button (🗑)**: Clears track memory with confirmation dialog

### 2.5 Quick Access Pills (Below Search Box)

Display existing tracks as clickable pills for quick switching:

```
[🔬 ML Security] [🤖 LLM] [📊 RAG] [📝 CV] [+ New Track]
```

| Element | Behavior |
|---------|----------|
| **Track Pill** | Click to activate & pre-fill related query |
| **Active Track** | Highlighted with border/background |
| **[+ New Track]** | Opens create track modal |

### 2.6 Search Results Section

**Initial State** (before search):
- Empty or show subtle prompt: "Enter a query to discover papers"
- Could show recent searches or trending topics

**After Search**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  Found 24 papers for "reranking for RAG"           [Sort: Relevance ▼]
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 📄 ColBERT-QA: Efficient Passage Reranking for RAG            │  │
│  │    Authors: Smith et al. • NeurIPS 2024 • ⭐ 142 citations     │  │
│  │    Proposes a late-interaction model for efficient...         │  │
│  │    [Save] [Like] [Cite]                                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 📄 Learning to Rank for RAG Pipelines                         │  │
│  │    ...                                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Mapping

### 3.1 What to Keep
| Current | New Location | Notes |
|---------|--------------|-------|
| Query input | Search box (center) | Main focus |
| Track list | Dropdown selector | Bottom-right of search box |
| New Track | Dropdown menu + Quick pill | Two access points |
| Build Context button | Search/Enter | Implicit action |
| Recommendations tab | Search results area | Shown after search |

### 3.2 What to Remove
| Element | Reason |
|---------|--------|
| Stage selector | Simplify - use auto/default |
| Exploration ratio | Advanced setting - hide or move to settings |
| Diversity strength | Advanced setting - hide or move to settings |
| Memory Inbox tab | Move to separate page or sidebar |
| Evals tab | Move to separate page or admin area |
| user_id input | Use session/auth (hidden) |

### 3.3 What to Move
| Element | From | To |
|---------|------|-----|
| Clear Track Memory | Tracks box | Track dropdown → "⚙ Manage Tracks" |
| Active indicator | Badge on track | Checkmark in dropdown |
| Refresh button | Header | Auto-refresh or remove |

---

## 4. User Flows

### 4.1 Primary Flow: Search for Papers
```
1. User lands on page
   → See centered search box with greeting

2. User types query "reranking methods for RAG"
   → Search box expands slightly as needed

3. User presses Enter or clicks 🔍
   → Loading indicator appears
   → Search box animates to top of page
   → Results appear below

4. User interacts with results
   → Save, Like, or Cite papers
```

### 4.2 Secondary Flow: Switch Track
```
1. User clicks track dropdown (showing "RAG")
   → Dropdown expands showing all tracks

2. User selects "ML Security"
   → Dropdown closes
   → Track indicator updates
   → (Optional) Query hint updates

3. User searches
   → Results filtered/weighted by track context
```

### 4.3 Tertiary Flow: Create New Track
```
1. User clicks "+ New Track" (pill or dropdown)
   → Modal opens

2. User enters track name and description
   → Clicks "Create"

3. Track created and activated
   → User can now search with new track context
```

---

## 5. Visual Design

### 5.1 Color Palette
| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| Background | `#faf9f7` (warm gray) | `#1a1a1a` |
| Search box | `#ffffff` | `#2d2d2d` |
| Search border | `#e5e5e5` | `#404040` |
| Focus border | `#d97706` (amber) | `#f59e0b` |
| Track pill active | `#fef3c7` | `#451a03` |
| Text primary | `#1f2937` | `#f9fafb` |

### 5.2 Typography
| Element | Font | Size | Weight |
|---------|------|------|--------|
| Greeting | System serif or Inter | 32-40px | 500 |
| Search input | Inter | 16px | 400 |
| Track selector | Inter | 14px | 500 |
| Result title | Inter | 18px | 600 |
| Result meta | Inter | 14px | 400 |

### 5.3 Spacing
| Element | Spacing |
|---------|---------|
| Search box padding | 16-20px |
| Search box border-radius | 16-24px |
| Result card gap | 12px |
| Track pill gap | 8px |

### 5.4 Animations
| Trigger | Animation |
|---------|-----------|
| Page load | Fade in + slide up (300ms) |
| Search submit | Search box slides to top (400ms ease-out) |
| Results appear | Staggered fade in (50ms delay each) |
| Dropdown open | Scale + fade (200ms) |

---

## 6. Technical Implementation

### 6.1 Component Structure
```
ResearchPage/
├── components/
│   ├── SearchBox.tsx           # Main search input with controls
│   ├── TrackSelector.tsx       # Dropdown for track selection
│   ├── TrackPills.tsx          # Quick access track buttons
│   ├── SearchResults.tsx       # Results container
│   ├── PaperCard.tsx           # Individual paper result
│   ├── CreateTrackModal.tsx    # New track creation
│   ├── EditTrackModal.tsx      # Edit existing track
│   └── ManageTracksModal.tsx   # Track management (edit, clear memory)
├── hooks/
│   ├── useSearch.ts            # Search state and API calls (TODO)
│   └── useTracks.ts            # Track management (TODO)
└── page.tsx                    # Main page component
```

> **Implementation Note**: Currently, state management is handled directly in `ResearchPageNew.tsx` rather than extracted to custom hooks. This may be refactored in Phase 4.

### 6.2 State Management
```typescript
interface ResearchPageState {
  // Search
  query: string;
  isSearching: boolean;
  hasSearched: boolean;  // Controls layout (centered vs top)
  results: Paper[];

  // Tracks
  tracks: Track[];
  activeTrack: Track | null;

  // UI
  isTrackDropdownOpen: boolean;
  isCreateModalOpen: boolean;
  isManageModalOpen: boolean;
}
```

### 6.3 API Endpoints Used
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /api/research/context` | Build context and get recommendations | ✅ Implemented |
| `GET /api/research/tracks` | List user's tracks | ✅ Implemented |
| `POST /api/research/tracks` | Create new track | ✅ Implemented |
| `PATCH /api/research/tracks/{id}` | Update track (name, description, keywords) | ✅ Implemented |
| `POST /api/research/tracks/{id}/activate` | Activate a track | ✅ Implemented |
| `POST /api/research/tracks/{id}/memory/clear` | Clear track memory | ✅ Implemented |

---

## 7. Migration Plan

### Phase 1: Component Refactor ✅ COMPLETE
1. ✅ Create new `SearchBox` component with integrated track selector
2. ✅ Create `TrackSelector` dropdown component
3. ✅ Create `TrackPills` quick access component
4. ✅ Create `PaperCard` component for search results
5. ✅ Create `SearchResults` container component
6. ✅ Create `CreateTrackModal` for new track creation
7. ✅ Create `ManageTracksModal` for track management

### Phase 2: Layout Change ✅ COMPLETE
1. ✅ Update `page.tsx` to centered layout
2. ✅ Implement search → top animation (CSS transitions)
3. ✅ Add results section with loading states
4. ✅ Fix alignment between greeting and search box
5. ✅ Increase content sizes for better readability

### Phase 3: Feature Parity ✅ COMPLETE
1. ✅ Track create operation works
2. ✅ Track activate operation works
3. ✅ Track clear memory operation works
4. ✅ Track edit operation works (EditTrackModal + PATCH API)
5. ✅ Search functionality works (returns paper recommendations)
6. ✅ Paper feedback actions (Save, Like, Dislike) with visual feedback
7. ✅ Paper card interactions with loading states
8. ✅ Track switching updates context

### Phase 4: Polish ✅ COMPLETE
1. ✅ Staggered fade-in animations for results
2. ✅ Responsive design (mobile-first breakpoints)
3. ✅ Dark mode support (inherits from shadcn/ui)
4. ⬜ Extract state to custom hooks (deferred - optional refactor)
5. ✅ Loading skeletons for search results
6. ⬜ Recent searches feature (deferred - future enhancement)

---

## 8. Open Questions

1. **Memory Inbox & Evals**: Where should these move? Options:
   - Separate pages in navigation
   - Tabs within a sidebar
   - Accessible from user menu

2. **Advanced Settings**: Should Stage/Exploration/Diversity be:
   - Completely removed
   - Hidden in an "Advanced" dropdown
   - Accessible via a settings gear icon

3. **Recent Searches**: Show recent searches before first search?

4. **Track Icons**: Allow users to set emoji/icons for tracks?

---

## Appendix: Wireframes

### A. Initial State (Before Search)
```
                    ┌─────────────────────────────┐
                    │                             │
                    │   📚 Good afternoon         │
                    │   What papers are you       │
                    │   looking for?              │
                    │                             │
                    │  ┌───────────────────────┐  │
                    │  │ Search for papers...  │  │
                    │  │                       │  │
                    │  │           [RAG ▼][🔍] │  │
                    │  └───────────────────────┘  │
                    │                             │
                    │  [RAG] [LLM] [CV] [+ New]   │
                    │                             │
                    └─────────────────────────────┘
```

### B. After Search (Results Showing)
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ reranking methods for RAG              [RAG ▼] [🔍]     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Found 24 papers                              [Sort: Relevance] │
│  ─────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ColBERT-QA: Efficient Passage Reranking for RAG         │    │
│  │ Smith et al. • NeurIPS 2024 • 142 citations             │    │
│  │ Proposes a late-interaction model for efficient...      │    │
│  │ [💾 Save] [👍 Like] [📋 Cite]                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Learning to Rank for Retrieval-Augmented Generation     │    │
│  │ ...                                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

---

## 9. Implementation History

| Date | Phase | Changes |
|------|-------|---------|
| 2026-02-11 | Phase 1 | Created all base components (SearchBox, TrackSelector, TrackPills, PaperCard, SearchResults, CreateTrackModal, ManageTracksModal) |
| 2026-02-11 | Phase 2 | Implemented centered layout with animation, connected to existing APIs |
| 2026-02-11 | Phase 2 | Fixed alignment issues, increased content sizes |
| 2026-02-11 | Phase 3 | Added EditTrackModal, changed Activate→Edit in ManageTracksModal, removed Close button, added PATCH API endpoint |
| 2026-02-11 | Phase 3 | Enhanced PaperCard with visual feedback for Save/Like/Dislike actions, per-card loading states |
| 2026-02-11 | Phase 4 | Added loading skeletons for search results |
| 2026-02-11 | Phase 4 | Added staggered fade-in animations for paper cards |
| 2026-02-11 | Phase 4 | Responsive design improvements (mobile-first breakpoints) |
| 2026-02-11 | Phase 4 | Created Skeleton UI component |

---

## 10. Summary of Delivered Features

### Core Functionality
- **Search**: Centered search box with track selector, Enter to submit
- **Track Management**: Create, edit, activate, and clear memory for tracks
- **Paper Results**: Card-based layout with title, authors, venue, year, citations, abstract
- **Feedback Actions**: Save, Like, Dislike with visual feedback and loading states

### UI/UX Enhancements
- **Claude-style Layout**: Centered greeting and search box, moves to top on search
- **Animations**: Page load fade-in, search transition, staggered results
- **Loading States**: Skeleton cards during search, per-action spinners
- **Responsive Design**: Mobile-optimized with breakpoints at sm (640px) and md (768px)

### API Endpoints
- `POST /api/research/context` - Build context and get recommendations
- `GET /api/research/tracks` - List user's tracks
- `POST /api/research/tracks` - Create new track
- `PATCH /api/research/tracks/{id}` - Update track (name, description, keywords)
- `POST /api/research/tracks/{id}/activate` - Activate a track
- `POST /api/research/tracks/{id}/memory/clear` - Clear track memory
- `POST /api/research/papers/feedback` - Record paper feedback

---

**Future Enhancements** (optional):
1. Extract state management to custom hooks (useSearch, useTracks)
2. Recent searches feature
3. Sort dropdown for results
4. Keyboard navigation for results
