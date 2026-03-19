```markdown
# Design System Specification: The Kinetic Vault

## 1. Overview & Creative North Star
This design system is built for speed, precision, and high-impact focus. Moving beyond the utility of a standard video tool, we are embracing a Creative North Star we call **"The Kinetic Vault."** 

The Kinetic Vault treats the interface not as a flat screen, but as a pressurized, high-performance environment. It utilizes a "Deep Dark" foundation to eliminate peripheral distractions, allowing content to "ignite" against the void. By moving away from traditional grid lines and opting for **intentional asymmetry** and **tonal layering**, we create an editorial experience that feels custom-tailored and premium. This is not just a tool; it is a high-speed digital instrument.

---

## 2. Color & Tonal Surface Theory
The palette is rooted in a high-contrast relationship between `surface` (#131313) and the aggressive energy of `primary` (#FFB4A8 / YouTube Red).

### The "No-Line" Rule
Standard UI relies on 1px borders to define space. **This design system prohibits them.** To create a high-end feel, boundaries must be defined exclusively through background color shifts.
- A card should not have an outline; it should exist as a `surface-container-low` (#1C1B1B) element sitting on a `surface` (#131313) backdrop.
- Use the **Spacing Scale** (e.g., `8` or `10`) to create "negative borders"—whitespace that acts as a structural separator.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the `surface-container` tiers to denote importance:
- **Base Level:** `surface` (#131313) or `surface-container-lowest` (#0E0E0E) for the main background.
- **Interactive Layer:** `surface-container` (#201F1F) for primary content areas.
- **Elevated Layer:** `surface-container-highest` (#353434) for temporary states or high-focus modals.

### The "Glass & Gradient" Rule
To inject "soul" into the minimalist aesthetic:
- **CTAs:** Use a subtle linear gradient transitioning from `primary` to `primary-container` (#FF5540) at a 45-degree angle.
- **Floating Elements:** Use `surface-bright` (#3A3939) with a 60% opacity and a `20px` backdrop-blur to create a "frosted glass" effect, ensuring the deep dark background bleeds through.

---

## 3. Typography: Editorial Authority
We utilize a clean, high-performance Sans-Serif (Inter/Roboto) to convey technical precision.

- **Display Scales (`display-lg` to `display-sm`):** Reserved for singular, high-impact moments. Use `display-lg` (3.5rem) for brand hero moments or empty-state "Flash" headlines.
- **Headlines & Titles:** Use `headline-md` (1.75rem) for task-based headers. The high contrast between `on_surface` (White) and `on_surface_variant` (Light Gray) is our primary tool for hierarchy.
- **Body & Labels:** All secondary information must use `body-md` or `label-md` in `on_surface_variant` (#AAAAAA). This "dims" the secondary information, keeping the user's focus on the primary task.

---

## 4. Elevation & Depth
In a line-free environment, depth is our only architecture.

### The Layering Principle
Instead of shadows, stack surface tiers. A `surface-container-high` card placed on a `surface-container-low` background creates a "soft lift" that feels architectural rather than "pasted on."

### Ambient Shadows
If a floating effect is required (e.g., a primary action button), use an **extra-diffused shadow**:
- **Blur:** 24dp - 32dp.
- **Opacity:** 8%.
- **Color:** Use a tinted version of `primary` (#FFB4A8) rather than pure black to simulate the glow of a red light source.

### The "Ghost Border" Fallback
If accessibility requires a container definition in high-glare environments, use a **Ghost Border**:
- **Token:** `outline-variant` (#603E39).
- **Opacity:** Strictly 10%–20%. It should be felt, not seen.

---

## 5. Components

### Primary Action Button (The "Flash" Button)
- **Height:** 56dp (as per `20` on the spacing scale) to ensure a high-end, tactile feel.
- **Corner Radius:** `md` (0.75rem / 12px) to provide a modern, friendly but professional edge.
- **Color:** Linear Gradient (`primary` to `primary-container`).
- **Typography:** `title-md` (1.125rem), Bold, `on_primary_fixed` (#410000).

### Content Cards
- **Structure:** No borders or dividers.
- **Background:** `surface-container-low` (#1C1B1B).
- **Padding:** `6` (1.5rem) internally to give the content "room to breathe."
- **Interaction:** On press, transition background to `surface-container-high` (#2A2A2A).

### Input Fields
- **Aesthetic:** Minimalist underline or soft-filled container.
- **Height:** 56dp.
- **Text:** Primary text in `on_surface` (White), Placeholder text in `on_surface_variant` (#AAAAAA) at 50% opacity.
- **Active State:** The bottom indicator should use the `primary` (#FFB4A8) token with a 2px thickness.

### Selection Chips
- **Unselected:** `surface-container-high` (#2A2A2A) with `on_surface_variant` text.
- **Selected:** `primary` background with `on_primary` text.
- **Shape:** `full` (9999px) for a pill-shaped "capsule" look.

---

## 6. Do's and Don'ts

### Do:
- **Embrace the Dark:** Use `surface-container-lowest` for 90% of the UI to preserve the "Deep Dark" brand identity.
- **Prioritize Touch:** Ensure every interactive element hits the **56dp** height threshold.
- **Use Asymmetric Spacing:** Use a larger top margin (`16` or `20`) than bottom margin on headers to create an editorial, "top-heavy" look.

### Don't:
- **No Divider Lines:** Never use a 1px line to separate list items. Use a `2` (0.5rem) vertical gap or a subtle background shift instead.
- **No High-Contrast Grays:** Avoid mid-tone grays. Stick to the extremes of the `surface` and `on_surface` tokens to maintain the high-end "OLED" look.
- **No Navigation Bars:** This system is for single-task focus. Use a large "Back" or "Close" icon (24dp) in the top-left if necessary, but avoid persistent bottom navigation.

### Accessibility Note:
While we use deep blacks and reds, ensure all `label-sm` text maintains a contrast ratio of at least 4.5:1 against its specific `surface-container` tier by using the `on_surface_variant` token appropriately.