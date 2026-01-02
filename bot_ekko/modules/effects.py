from bot_ekko.sys_config import CYAN, MAIN_FONT

class EffectsRenderer:
    def render_zzz(self, surface, particles):
        for p in particles:
            # p is [x, y, alpha]
            if len(p) >= 3:
                z_surf = MAIN_FONT.render("Z", True, CYAN)
                z_surf.set_alpha(p[2])
                surface.blit(z_surf, (p[0], p[1]))
