import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/** 仅用于生成本地演示账号的 BCrypt 哈希，不参与应用运行。 */
class ForumPassword
{
    public static void main(String[] args)
    {
        System.out.println(new BCryptPasswordEncoder().encode(args[0]));
    }
}
