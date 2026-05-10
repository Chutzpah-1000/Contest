# Apple iOS Design Guide for Claude

This document is based on Apple’s Human Interface Guidelines. Use it when designing iOS app interfaces. The result should feel natural, quiet, clear, touch-friendly, and at home on iPhone.

## 1. Core Philosophy

- Content is the focus. UI should support the content, not compete with it.
- Reduce the number of visible controls and help people focus on the primary task.
- Reveal secondary information and secondary actions only when needed.
- iPhone is used one-handed or two-handed, so important controls should be reachable, especially in the middle or lower part of the screen.
- People may use an app for a few seconds or for a long session, so support both quick entry and stable navigation.
- Prefer familiar iOS system patterns over unfamiliar custom UI.

## 2. Layout

- Respect the Safe Area.
- Avoid collisions with Dynamic Island, the Home indicator, status bar, tab bar, and toolbar.
- Backgrounds and scrollable content should extend naturally to the screen edges.
- Group related items using spacing, separators, background levels, or materials.
- Make essential information visible immediately. Do not crowd the screen with secondary details.
- Avoid overusing full-width buttons on iOS. Buttons should usually be inset from the screen edges.
- Support both portrait and landscape when appropriate.
- Do not hide the status bar unless the experience is immersive, such as games or media playback.

## 3. Navigation

- Use a Tab Bar for top-level sections.
- A Tab Bar is for navigation, not actions.
- Each tab should have a short label and an SF Symbols-style icon.
- Keep the Tab Bar visible and consistent while people navigate.
- Use a Toolbar for actions related to the current view.
- Put only the most important actions in the main toolbar area. Move secondary actions into a More menu.
- Use Large Titles when they help people understand where they are.
- Use standard Back and Close behavior and icons.

## 4. Buttons

- Buttons initiate immediate actions.
- Every tappable control should have a hit area of at least 44x44 pt.
- Custom buttons must include pressed, disabled, and loading states.
- Use only one, or at most two, visually prominent primary buttons per screen.
- Use a primary button only for the safest and most likely action.
- Never make a destructive action the primary button.
- Communicate priority through style, not through inconsistent button sizes.
- Use text when a short label is clearer than an icon.
- Button labels should be short and action-oriented. Examples: Save, Add, Share, Continue.
- For actions that take time, show a loading indicator and a progress label inside the button.

## 5. Color

- Prefer system colors and semantic colors.
- Use color consistently. Do not use the same color to mean different things.
- Never rely on color alone to communicate state or meaning. Pair it with text, icons, or shape.
- Test colors in Light Mode, Dark Mode, and Increased Contrast.
- If using custom colors, provide light, dark, and high-contrast variants.
- If content is colorful, keep controls, toolbars, and tab bars mostly monochrome.
- Use accent color only where it adds meaning: primary actions, selected states, or status indicators.
- Do not apply strong accent backgrounds to many controls at once.

## 6. Liquid Glass and Materials

- Use Liquid Glass for functional layers floating above content, such as controls and navigation.
- Do not use Liquid Glass as ordinary content styling.
- Use Liquid Glass sparingly. Reserve it for important functional elements.
- Prefer system behavior for tab bars, toolbars, and sidebars.
- Use standard materials, blur, vibrancy, and background levels to separate content areas.
- Text and icons on glass or translucent materials must always maintain strong contrast.

## 7. Typography

- Follow the feel of Apple’s SF Pro system typography.
- Design as if Dynamic Type is supported.
- Text should remain readable and useful when the user increases font size.
- At large accessibility sizes, consider changing horizontal layouts into stacked vertical layouts.
- Maintain information hierarchy across all text sizes.
- Clearly distinguish titles, body text, secondary text, and metadata.
- Do not use oversized headings inside compact cards or panels.
- Ensure strong contrast between text and its background.

## 8. Icons and SF Symbols

- Icons should follow the SF Symbols style.
- Use familiar symbols for familiar actions, such as share, search, add, and delete.
- Filled symbols usually work well for tab bars and selected states.
- Outline symbols usually work well in toolbars and lists.
- Icons should be simple, recognizable, inclusive, and directly related to their action or content.
- If an icon alone is unclear, provide a short label, tooltip, or accessibility label.
- Match icon weight and size to nearby text.

## 9. Accessibility

- Accessibility is a core design requirement, not an afterthought.
- All primary controls need at least a 44x44 pt tap target.
- Provide enough spacing between controls.
- Do not communicate meaning with color alone.
- Provide clear labels for VoiceOver.
- Consider Dynamic Type, Bold Text, Increase Contrast, and Reduce Transparency.
- Prevent text from truncating, overlapping, or becoming unreadable.
- Important icons should scale along with larger text sizes.

## 10. Claude Output Rules

When Claude proposes or implements an iOS UI, follow these rules:

- Do not create a marketing-style landing page unless explicitly requested.
- The first screen should be a usable app screen.
- Avoid decorative gradients, excessive cards, heavy shadows, and meaningless glass effects.
- Do not overload a screen with too many buttons, badges, or labels.
- Prioritize spacing, hierarchy, system components, and bottom-reachable controls.
- Place important actions where they are easy to reach.
- Hide secondary actions in menus, swipe actions, detail views, or More buttons.
- Every screen must work in Light Mode, Dark Mode, and larger text sizes.
- The final UI should feel like a product people can use every day, not a flashy concept mockup.
