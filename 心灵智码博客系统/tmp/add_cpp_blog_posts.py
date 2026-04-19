import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fullwebproject.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from blog.models import Post, Category, Tag

User = get_user_model()

# 获取或创建作者（使用第一个用户）
try:
    author = User.objects.first()
    if not author:
        print("没有找到用户，请先创建用户")
        exit(1)
except Exception as e:
    print(f"获取用户失败: {e}")
    exit(1)

# 获取或创建C++分类
try:
    category, created = Category.objects.get_or_create(
        name="C++",
        slug="cpp"
    )
    if created:
        category.description = "C++编程相关文章"
        category.save()
except Exception as e:
    print(f"创建分类失败: {e}")
    exit(1)

# 获取或创建标签
tags = []
tag_names = ["C++", "编程", "技术", "性能优化", "内存管理"]
for tag_name in tag_names:
    try:
        tag, created = Tag.objects.get_or_create(
            name=tag_name,
            slug=tag_name.lower().replace(" ", "-")
        )
        tags.append(tag)
    except Exception as e:
        print(f"创建标签 {tag_name} 失败: {e}")

# C++相关文章
cpp_articles = [
    {
        "title": "C++11新特性详解",
        "content": "C++11引入了许多新特性，包括自动类型推导、Lambda表达式、右值引用、智能指针等。这些特性大大提高了C++的编程效率和代码可读性。\n\n**自动类型推导**\n使用`auto`关键字可以让编译器自动推导变量类型，减少代码冗余。\n\n**Lambda表达式**\nLambda表达式允许在需要的地方定义匿名函数，简化代码结构。\n\n**右值引用**\n右值引用和移动语义可以提高代码性能，减少不必要的拷贝操作。\n\n**智能指针**\n智能指针（`unique_ptr`、`shared_ptr`、`weak_ptr`）可以自动管理内存，避免内存泄漏。\n\n这些新特性使得C++代码更加现代、安全和高效。",
        "slug": "cpp11-new-features"
    },
    {
        "title": "C++内存管理详解",
        "content": "C++的内存管理是C++编程中的重要部分，包括栈内存、堆内存的分配与释放。\n\n**栈内存**\n栈内存由编译器自动管理，用于存储局部变量和函数参数。栈内存的分配和释放速度快，但空间有限。\n\n**堆内存**\n堆内存由程序员手动管理，使用`new`和`delete`操作符进行分配和释放。堆内存空间较大，但分配和释放速度较慢。\n\n**智能指针**\nC++11引入了智能指针，可以自动管理堆内存的释放，避免内存泄漏。\n\n**内存泄漏**\n内存泄漏是指程序分配的内存没有被正确释放，导致内存使用量不断增加。使用智能指针和RAII原则可以有效避免内存泄漏。\n\n**内存优化**\n合理使用内存池、减少内存碎片、优化数据结构等方法可以提高程序的内存使用效率。",
        "slug": "cpp-memory-management"
    },
    {
        "title": "C++ STL容器使用指南",
        "content": "C++ STL（标准模板库）提供了丰富的容器类，包括vector、list、map、set等。\n\n**序列容器**\n- `vector`：动态数组，随机访问速度快，适合频繁访问元素的场景。\n- `list`：双向链表，插入和删除操作速度快，适合频繁修改的场景。\n- `deque`：双端队列，支持两端的快速插入和删除。\n\n**关联容器**\n- `map`：键值对映射，基于红黑树实现，查找时间复杂度为O(log n)。\n- `set`：有序集合，基于红黑树实现，查找时间复杂度为O(log n)。\n- `unordered_map`：哈希表实现的键值对映射，平均查找时间复杂度为O(1)。\n- `unordered_set`：哈希表实现的集合，平均查找时间复杂度为O(1)。\n\n**容器适配器**\n- `stack`：栈，后进先出。\n- `queue`：队列，先进先出。\n- `priority_queue`：优先队列，自动排序。\n\n选择合适的容器可以提高程序的性能和代码的可读性。",
        "slug": "cpp-stl-containers"
    },
    {
        "title": "C++多线程编程入门",
        "content": "C++11引入了标准的多线程库，使得多线程编程变得更加简单和安全。\n\n**线程的创建与管理**\n使用`std::thread`类可以创建和管理线程。\n\n**互斥锁**\n使用`std::mutex`和`std::lock_guard`可以保护共享资源，避免线程竞争。\n\n**条件变量**\n使用`std::condition_variable`可以实现线程间的通信和同步。\n\n**原子操作**\n使用`std::atomic`可以实现无锁的线程安全操作。\n\n**线程池**\n线程池可以重用线程，减少线程创建和销毁的开销。\n\n**并发容器**\nC++17引入了`std::atomic`、`std::shared_mutex`等并发工具，C++20引入了`std::jthread`等新特性。\n\n多线程编程可以充分利用多核CPU的性能，但也需要注意线程安全和同步问题。",
        "slug": "cpp-multithreading"
    },
    {
        "title": "C++面向对象编程最佳实践",
        "content": "面向对象编程是C++的核心特性之一。\n\n**类的设计原则**\n- 单一职责原则：一个类应该只负责一项职责。\n- 开放封闭原则：类应该对扩展开放，对修改封闭。\n- 里氏替换原则：子类应该可以替换父类。\n- 依赖倒置原则：依赖于抽象，不依赖于具体实现。\n- 接口隔离原则：接口应该小而专一。\n\n**继承与多态**\n使用继承可以复用代码，使用多态可以实现运行时的动态绑定。\n\n**虚函数**\n虚函数是实现多态的关键，通过虚函数表实现运行时多态。\n\n**抽象类与接口**\n抽象类可以定义接口，强制子类实现特定的方法。\n\n**封装**\n封装可以隐藏实现细节，提高代码的可维护性和安全性。\n\n**构造函数与析构函数**\n合理使用构造函数和析构函数可以确保资源的正确初始化和释放。",
        "slug": "cpp-oop-best-practices"
    },
    {
        "title": "C++模板编程详解",
        "content": "C++模板是C++的强大特性之一，支持泛型编程。\n\n**函数模板**\n函数模板可以定义通用的函数，支持不同类型的参数。\n\n**类模板**\n类模板可以定义通用的类，支持不同类型的成员变量和方法。\n\n**模板特化**\n模板特化可以为特定类型提供专门的实现。\n\n**变参模板**\n变参模板可以接受任意数量的参数。\n\n**模板元编程**\n模板元编程可以在编译时执行计算，提高程序的运行时性能。\n\n**SFINAE**\nSFINAE（Substitution Failure Is Not An Error）是模板编程中的重要概念，可以根据类型特性选择不同的重载。\n\n模板编程可以提高代码的复用性和灵活性，但也会增加编译时间和代码复杂度。",
        "slug": "cpp-template-programming"
    },
    {
        "title": "C++异常处理机制",
        "content": "C++异常处理是C++语言提供的错误处理机制。\n\n**try-catch语句**\n使用try-catch语句可以捕获和处理异常。\n\n**异常的抛出**\n使用throw语句可以抛出异常。\n\n**异常的类型**\n异常可以是任何类型，通常使用专门的异常类。\n\n**异常安全**\n异常安全是指程序在发生异常时能够保持一致的状态。\n\n**noexcept**\nC++11引入了noexcept关键字，可以声明函数不会抛出异常。\n\n**异常规格**\nC++11之前使用异常规格（throw()）来声明函数可能抛出的异常类型，C++11后推荐使用noexcept。\n\n合理使用异常处理可以提高程序的健壮性，但也会增加运行时开销。",
        "slug": "cpp-exception-handling"
    },
    {
        "title": "C++性能优化技巧",
        "content": "C++是一种高性能的编程语言，但要充分发挥其性能潜力，需要掌握一些优化技巧。\n\n**编译器优化**\n使用-O2、-O3等编译器优化选项可以提高程序性能。\n\n**内存访问优化**\n- 减少缓存未命中：使用连续的内存布局，避免随机访问。\n- 减少内存分配：使用对象池、预分配内存等方法。\n- 使用移动语义：减少不必要的拷贝操作。\n\n**算法选择**\n选择合适的算法可以显著提高程序性能。\n\n**并行计算**\n使用多线程、SIMD指令等方法可以充分利用硬件性能。\n\n**避免运行时开销**\n- 使用内联函数：减少函数调用开销。\n- 使用const和constexpr：允许编译器进行更多优化。\n- 避免虚函数：减少运行时多态的开销。\n\n**性能分析**\n使用性能分析工具（如gprof、Valgrind等）可以找出性能瓶颈。\n\n性能优化需要在代码可读性和性能之间找到平衡。",
        "slug": "cpp-performance-optimization"
    },
    {
        "title": "C++与C的区别与联系",
        "content": "C++是在C语言的基础上发展而来的，两者既有联系又有区别。\n\n**语法差异**\n- C++增加了类、继承、多态等面向对象特性。\n- C++增加了模板、命名空间、异常处理等现代特性。\n- C++支持函数重载、运算符重载等特性。\n\n**类型系统**\n- C++的类型系统更加严格，提供了更多的类型安全保障。\n- C++增加了引用类型，提供了更安全的指针替代方案。\n\n**标准库**\n- C++标准库比C标准库更加丰富，包括STL、智能指针等。\n- C++标准库提供了更多的高级功能，如容器、算法、迭代器等。\n\n**编程风格**\n- C倾向于过程式编程，C++支持过程式、面向对象、泛型编程等多种编程范式。\n- C++代码通常更加抽象和模块化。\n\n**兼容性**\n- C++兼容大部分C代码，可以直接使用C标准库。\n- C代码需要进行适当的修改才能在C++中编译。\n\nC和C++各有优缺点，选择哪种语言取决于具体的应用场景。",
        "slug": "cpp-vs-c"
    },
    {
        "title": "C++20新特性介绍",
        "content": "C++20引入了许多新特性，包括概念（Concepts）、范围库（Ranges）、协程（Coroutines）等。\n\n**概念（Concepts）**\n概念可以约束模板参数的类型，提高模板代码的可读性和错误信息的清晰度。\n\n**范围库（Ranges）**\n范围库提供了一种更简洁、更灵活的方式来处理序列数据。\n\n**协程（Coroutines）**\n协程允许函数在执行过程中暂停和恢复，简化异步编程。\n\n**模块（Modules）**\n模块可以替代头文件，提高编译速度和代码组织。\n\n**三路比较运算符（<=>）**\n三路比较运算符可以简化比较操作的实现。\n\n**constexpr增强**\nC++20扩展了constexpr的能力，允许在编译时执行更多的操作。\n\n**日历和时区库**\nC++20引入了标准的日历和时区库，提供了处理日期和时间的功能。\n\n**格式化库**\nC++20引入了标准的格式化库，提供了类似printf的格式化功能。\n\n这些新特性使得C++代码更加现代、安全和高效。",
        "slug": "cpp20-new-features"
    }
]

# 添加文章
for article in cpp_articles:
    try:
        # 检查文章是否已存在
        existing_post = Post.objects.filter(slug=article["slug"]).first()
        if existing_post:
            print(f"文章 {article['title']} 已存在，跳过")
            continue
        
        # 创建文章
        post = Post(
            title=article["title"],
            slug=article["slug"],
            content=article["content"],
            excerpt=article["content"][:200] + "...",
            author=author,
            category=category,
            is_published=True,
            publish_date=timezone.now()
        )
        post.save()
        
        # 添加标签
        post.tags.set(tags)
        
        print(f"成功添加文章: {article['title']}")
    except Exception as e:
        print(f"添加文章 {article['title']} 失败: {e}")

print("\nC++博客文章添加完成！")
