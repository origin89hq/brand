"""Shared render quality while preserving Buddy's authored coat and lighting.

Keep the smooth, directional shoulder and beard groom in the editable model.
Small-avatar readability is handled by dedicated cameras and responsive exports.
"""


def render_quality(scene, samples=192, fur=True):
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .006 if fur else .01
    scene.cycles.adaptive_min_samples = 64 if fur else 32
    scene.camera.data.dof.use_dof = False


def apply(scene):
    render_quality(scene)
    scene['finish'] = 'Smooth directional coat and soft studio lighting; fine strand rendering'
