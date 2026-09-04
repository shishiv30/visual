package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Test

class SkillTreeLayoutTest {
    @Test
    fun currentIndexFallsBackToLast() {
        val nodes = listOf(
            TreeNode("a", "A"),
            TreeNode("b", "B"),
            TreeNode("c", "C"),
        )
        assertEquals(2, SkillTreeLayout.currentIndex(nodes))
        assertEquals(1, SkillTreeLayout.currentIndex(nodes.mapIndexed { i, n -> n.copy(current = i == 1) }))
    }

    @Test
    fun kindsMatchDesktopColors() {
        assertEquals(SkillTreeLayout.Kind.COMPLETED, SkillTreeLayout.kind(0, 1))
        assertEquals(SkillTreeLayout.Kind.CURRENT, SkillTreeLayout.kind(1, 1))
        assertEquals(SkillTreeLayout.Kind.PENDING, SkillTreeLayout.kind(2, 1))
        assertEquals(0xFFE1BEE7.toInt(), SkillTreeLayout.color(SkillTreeLayout.Kind.CURRENT))
        assertEquals(0xFFCE93D8.toInt(), SkillTreeLayout.color(SkillTreeLayout.Kind.COMPLETED))
        assertEquals(0xFF757575.toInt(), SkillTreeLayout.color(SkillTreeLayout.Kind.PENDING))
        assertEquals(0xFFF5F5F5.toInt(), SkillTreeLayout.LINE)
    }

    @Test
    fun heightCoversEveryNode() {
        assertEquals(36, SkillTreeLayout.heightPx(0, 1f))
        assertEquals(108, SkillTreeLayout.heightPx(3, 1f))
        assertEquals(216, SkillTreeLayout.heightPx(3, 2f))
    }
}
