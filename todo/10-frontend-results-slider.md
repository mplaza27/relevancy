[x]
# Prompt 10: Frontend Results & Relevancy Slider

## Goal
Implement the relevancy slider for threshold control and the card results list with expandable details.

## Context
- Location: `frontend/src/components/`
- The API returns ALL matches with similarity scores in one response
- The slider filters client-side via `useMemo` — no re-query needed
- Cards show: text (with cloze visible), similarity %, tags, expandable detail fields
- shadcn/ui components already installed: Slider, Accordion, Badge, Card

## Files to Implement

### 1. `frontend/src/components/RelevancySlider.tsx`

Uses shadcn/ui `Slider` (built on Radix UI — accessible, keyboard navigable).

Props:
- `value: number` (0.0 - 1.0)
- `onChange: (value: number) => void`
- `totalCards: number`
- `filteredCards: number`

UI layout:
```
Relevancy Threshold                    142 / 856 cards
[═══════════●══════════════════════════════════════]
0.0 - More cards          0.30          1.0 - Fewer cards
```

- Show current count: `{filteredCards} / {totalCards} cards`
- Show threshold value as number: `0.30`
- Step size: 0.01 for fine control
- Default value: 0.3 (reasonable starting threshold)

### 2. `frontend/src/components/CardList.tsx`

Uses shadcn/ui `Accordion` for expandable cards.

Props:
- `cards: MatchedCard[]` (already filtered by threshold)

Each card row shows:
- **Similarity badge**: `87%` in a `Badge` component
- **Card text**: Main text with cloze deletions shown (the text field already has cloze stripped from backend, but render as-is)
- **Expand arrow**: Click to expand

Expanded view shows:
- Extra field content
- Resource fields from `raw_fields`: Pathoma, Boards and Beyond, First Aid, Sketchy (only if non-empty)
- Tags as `Badge` components, formatted: `#AK_Step1::FirstAid::Cardio` → `Step1 > FirstAid > Cardio`

```tsx
<Accordion type="multiple">
  {cards.map(card => (
    <AccordionItem key={card.note_id} value={String(card.note_id)}>
      <AccordionTrigger>
        <div className="flex items-center gap-3 text-left w-full">
          <Badge variant="outline" className="shrink-0 font-mono">
            {(card.similarity * 100).toFixed(0)}%
          </Badge>
          <span className="truncate flex-1">{card.text}</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        {/* Extra, Pathoma, B&B, First Aid, Sketchy fields */}
        {/* Tags as badges */}
      </AccordionContent>
    </AccordionItem>
  ))}
</Accordion>
```

**Tag formatting helper:**
```typescript
function formatTag(tag: string): string {
  return tag
    .replace(/^#/, "")
    .replace(/AK_Other::/g, "")
    .replace(/AK_Step1_v12::/g, "Step1 > ")
    .replace(/AK_Step2_v12::/g, "Step2 > ")
    .replaceAll("::", " > ");
}
```

Only show the first 5-8 tags per card to avoid clutter. Show a "+N more" badge if there are more.

**Resource fields to display** (from `raw_fields` JSONB):
- Pathoma
- Boards and Beyond
- First Aid
- Sketchy
- OME
- Additional Resources

Only render fields that have non-empty content. Strip HTML from these fields before display (or render as HTML if safe — the content is from a trusted Anki deck).

**Empty state:**
If `cards.length === 0`, show: "No cards match at this threshold. Try lowering the slider."

### 3. Performance considerations
- The card list could have hundreds of items. Use `Accordion type="multiple"` so expanding one doesn't collapse others.
- Consider virtualizing the list if > 500 cards (e.g., `@tanstack/react-virtual`), but for MVP this is likely unnecessary since the slider filters most results.
- Tag badge rendering for 200+ cards × 5+ tags each could be slow — memoize the tag formatting.

## Integration with App.tsx

Update `App.tsx` to replace placeholders with real components:

```tsx
{results && (
  <>
    <RelevancySlider
      value={threshold}
      onChange={setThreshold}
      totalCards={results.cards.length}
      filteredCards={filteredCards.length}
    />
    <CardList cards={filteredCards} />
    <SyncToAnki ... />  {/* Implemented in prompt 11 */}
  </>
)}
```

## Verification
- Slider moves smoothly, card count updates in real-time
- Cards expand/collapse independently
- Tags render cleanly with hierarchical formatting
- Resource fields only appear when they have content
- Empty state shows when threshold is too high
- Performance is acceptable with 200+ cards visible
