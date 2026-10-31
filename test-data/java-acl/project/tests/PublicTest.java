public class PublicTest {
    public static void main(String[] args) {
        if (!"Acl".equals(AccessLabel.label())) {
            throw new AssertionError("label");
        }
        System.out.println("public ok");
    }
}
