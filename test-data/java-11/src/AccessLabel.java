public class AccessLabel {
    public static String label() {
        return java.security.acl.Acl.class.getSimpleName();
    }

    public static String family() {
        return java.security.acl.Acl.class.getPackageName();
    }
}
