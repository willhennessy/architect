# Interactive Diagram Prompt Template

This reference defines how to construct a prompt that instructs Claude Imagine to build an interactive, drill-down architecture diagram from the generated architecture artifacts.

## Role Assignment

Assign Claude Imagine a role rooted in the technical expertise of this particular architecture AND in interactive visualization design. For example: "You are a senior Rust engineer and interactive visualization designer."

## Context

* Point the agent to the architecture artifacts (included in the bundle).
* Explain the C4 model structure: the artifacts contain a canonical model (`model.yaml`) plus derived views at multiple abstraction levels (system context, container, component, and optionally code-level).
* Explain that each level maps to a progressively deeper view of the system.

## Interactive Drill-Down Behavior

The prompt MUST instruct Claude Imagine to build a single interactive diagram with the following behaviors:

### Navigation model — progressive drill-down

1. **Entry view: System Context.** The diagram opens at the highest level showing the system of interest, external actors (people, external systems), and their relationships. Each element in the system of interest that contains child elements (containers) MUST be visually clickable.
2. **Level 2: Container view.** When the user clicks on the system of interest (or a specific bounded context within it), the diagram transitions to show the containers within that boundary — deployable units, datastores, queues, and their relationships. Each container that has a corresponding component view MUST be visually clickable.
3. **Level 3: Component view.** When the user clicks on a container, the diagram transitions to show the components within that container — internal modules, services, and their relationships. Each component that has deeper code-level detail available MUST be visually clickable.
4. **Level 4: Code detail (when available).** When the user clicks on a component at the deepest level, display the code-level detail — key classes, functions, interfaces, and their relationships. If no code-level view exists for that component, display a detail panel with the component's description, technology, responsibilities, and owned data instead of navigating deeper.

### Breadcrumb navigation — always show current position

* At all times, display a breadcrumb path at the top of the diagram showing the user's current navigation depth.
* Format: `System Name > Container Name > Component Name` (showing only the levels currently drilled into).
* At the entry view, the breadcrumb shows only the system name.
* Each breadcrumb segment MUST be clickable to navigate back to that level.
* Include a "Back" control to return to the parent level.

### Visual affordances

* Clickable elements MUST have a visual indicator that they can be drilled into (e.g., a subtle expand icon, a different border style, or a hover effect that signals interactivity).
* Elements with no children should NOT appear clickable.
* Transitions between levels should feel smooth — use animation or a clear visual transition so the user understands they have moved deeper or shallower in the hierarchy.
* Use consistent color coding across levels to help the user track element types (e.g., containers always use one color family, external systems another, datastores another).

### Relationship rendering

* At each level, render the relationships defined in the architecture model for the elements currently in view.
* Label relationships with their description and protocol/technology when available.
* Relationships to elements outside the current view (e.g., a component communicating with an external system) should show the external element as a simplified reference node at the edge of the diagram, not fully expanded.

### Detail panels

* When a user clicks on any element (at any level), show a detail panel or tooltip containing:
  * Element name and type
  * Technology/language
  * Description and responsibilities
  * Owned data (if applicable)
  * Confidence level (confirmed / strong_inference / weak_inference)
* The detail panel should not replace the drill-down navigation — clicking to drill down and clicking to inspect should be distinguishable (e.g., double-click or a dedicated "expand" icon to drill down, single-click to inspect).

### Data sourcing rules

* All elements, relationships, and metadata MUST be sourced from the provided architecture artifacts (`model.yaml` and `views/*.yaml`).
* Do not invent elements, relationships, or metadata not present in the artifacts.
* If a view file exists for a container or component, use it to populate that drill-down level. If no view file exists, that element is a leaf node — show its detail panel on click instead of drilling down.
* Use `manifest.yaml` to determine which views are available and map them to drill-down levels.

## Layout and Style Guidance

* Use a clean, professional aesthetic suitable for engineering teams.
* Optimize for readability — avoid visual clutter.
* Sequence views (if present in the architecture artifacts) should be accessible from a separate tab or panel, not mixed into the drill-down hierarchy.
* The diagram should be fully self-contained in a single HTML page with inline CSS and JavaScript — no external dependencies.
