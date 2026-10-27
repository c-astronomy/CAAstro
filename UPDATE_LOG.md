# AstroControl Update Log

## 2026-10-27 — Major fixes applied
- Fixed DSLR/image viewer capture-to-display pipeline (was never retrieving ImageArray after capture).
- Remade planetarium: proper alt/az circular projection, manual mount sync, constellations + Messier + NGC objects embedded.
- Expanded object database: 30+ Messier objects, 20+ NGC objects, 12 major constellations with line data.
- Verified all button connections across mount, focus, guiding, sequencer, planetarium, image viewer, filter, polar align, status widgets.
- Added DSLR-specific fallback for image retrieval.
- All files updated; this log maintained.
- Fixed _radec_to_altaz ephem compute (used obj.compute(observer) for v4.2.1).
- Fixed duplicate lbl_guide_status in guiding_widget.py.
- Fixed focus_widget _stop_focus to call Halt/Abort.
- Fixed mount_widget _slew_dir to try MoveAxis properly.
- Fixed sequencer _run_sequence / _stop_sequence with _stop_requested flag.
- All button connections tested; syntax verified.
- Planetarium: clarified "Visual Preview" label; added site settings (lat/lon) with Apply button.
- App: split left device panel: top = device tree, bottom = Device Settings/config area.
- Added astro_control/config.py (JSON profile persistence).
- Planetarium: load/save site lat/lon via astro_config.json.
- Sequencer: Save Profile / Load Profile buttons (profiles/ folder, JSON steps).
- Added theme switcher: Light (white/black), Dark (green #00ff88, default), Alt Red-Green (#ff5555/#ffaa00).
- Located in left panel top above control buttons as a combo box.
- Default is Dark; restart needed to change (or switch at runtime).
