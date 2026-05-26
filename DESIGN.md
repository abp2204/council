# UI Vision: Neo-Academic Legal Gothic

## 1. Aesthetic Identity
- **Keywords**: Pristine, Harvard Law, Roman/Greek Pillars, Gothic Architecture, Modern Tech-Infused, Harvey Specter.
- **Vibe**: Immersive, authoritative, and sophisticated. The feeling of being in an elite legal environment like an ancient library or a high-tech courtroom. It's "Harvey Specter meets Gothic Academia."
- **Color Palette**: 
  - **Background**: Deep Charcoal and Midnight Walnut (#1A1A1A, #2C1E1E)
  - **Primary**: Rich Browns and Burnished Wood tones
  - **Accent**: Glowing Amber and Polished Gold (#D4AF37, #FFD700)
  - **Text**: Stark White and Ivory for readability and order (#FFFFFF, #F5F5F0)
- **Typography**: 
  - **Headings**: Elegant Serifs (e.g., Playfair Display or Cinzel) to evoke legal tradition and architecture.
  - **UI/Body**: High-precision Sans-Serifs (e.g., Inter or Roboto Mono) to maintain the "modern tech" feel.

## 2. Structural Changes (Layout)
- **The Arena**: A central column for the main transcript (Opposing side and Judge). This "middle lane" is the focus of the architectural framing.
- **The Archives**: Floating "document" tooltips or side panels that emerge from the edges, containing real case documents for context.
- **The Pillars**: UI dividers that subtly mimic Greek/Roman columns or Gothic arches, providing a sense of structural permanence and order.

## 3. Key Components
- **The Transcript**: Centrally justified. Speech bubbles or blocks with sharp, clean borders. Judge's interjections styled differently (perhaps with a "gold" glow) from the opposing agent.
- **The Document Desk**: Contextual tooltips/popovers that reveal high-fidelity document scans or legal text when hovered or clicked.
- **Voice Interface**: A "modern/techie" visualization (e.g., a glowing waveform in amber) that pulses within the clean architectural frame.

## 4. Interactive Details
- **Feedback**: Soft glows on hover, transitions that feel like "turning a page" or "opening a heavy door."
- **Modality**: Seamless transition between voice-driven arguments and manual document review.

## 5. Implementation Directives
- **Primary Files to Modify**:
  - `frontend/app/globals.css`: To define the "Gothic Tech" theme, custom scrollbars (wood/gold), and the palette.
  - `frontend/app/layout.tsx`: To wrap the app in the "Neo-Academic" shell.
  - `frontend/app/page.tsx`: Redesign the lobby/landing to reflect the elite library feel.
  - `frontend/app/session/page.tsx`: Implementation of the central chat and document tooltips.
- **Dependencies needed**:
  - `framer-motion`: For the sophisticated architectural transitions.
  - `lucide-react`: For clean, modern icons.
  - Google Fonts: Cinzel/Playfair Display and Inter.
